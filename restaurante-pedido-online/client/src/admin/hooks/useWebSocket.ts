import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ADMIN_QUERY_KEYS } from "@/admin/hooks/useAdminQueries";

// ─── Tipos de eventos que o servidor envia ──────────────
export type WsEventTipo =
  | "novo_pedido"
  | "pedido_atualizado"
  | "pedido_cancelado"
  | "pedido_despachado"
  | "entrega_atrasada"
  | "entrega_finalizada"
  | "tempo_ajustado"
  | "tempo_medio_atualizado"
  | "motoboy_posicao"
  | "mesa_paga"
  | "config_atualizada"
  | "pix_confirmado"
  | "printer_status"
  | "print_ack"
  | "reimprimir_pedido"
  | "bot_mensagem"
  | "bot_atraso_detectado"
  | "bot_handoff_solicitado"
  | "ping";

export interface WsEvent {
  tipo: WsEventTipo;
  dados?: Record<string, unknown>;
}

// ─── Sons distintos via Web Audio API ────────────────────
// Cada evento tem timbre, frequência e padrão únicos para
// que o atendente identifique pelo som o que está acontecendo.

/** Novo pedido: 3 bips agudos rápidos (sine 880Hz) — "tin tin tin" */
function tocarSomNotificacao() {
  try {
    const ctx = new AudioContext();
    const tempos = [0, 0.15, 0.3];
    tempos.forEach((t) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      osc.type = "sine";
      gain.gain.setValueAtTime(0.4, ctx.currentTime + t);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.12);
      osc.start(ctx.currentTime + t);
      osc.stop(ctx.currentTime + t + 0.12);
    });
  } catch {
    // AudioContext não disponível
  }
}

/** Entrega atrasada: 4 bips graves urgentes (square 440Hz) — alarme */
function tocarSomAlerta() {
  try {
    const ctx = new AudioContext();
    const tempos = [0, 0.25, 0.5, 0.75];
    tempos.forEach((t) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 440;
      osc.type = "square";
      gain.gain.setValueAtTime(0.3, ctx.currentTime + t);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.2);
      osc.start(ctx.currentTime + t);
      osc.stop(ctx.currentTime + t + 0.2);
    });
  } catch {
    // AudioContext não disponível
  }
}

/** Pedido cancelado: tom descendente triste (sawtooth 660→330Hz) */
function tocarSomCancelamento() {
  try {
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(660, ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(330, ctx.currentTime + 0.5);
    gain.gain.setValueAtTime(0.25, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.6);
  } catch {
    // AudioContext não disponível
  }
}

/** Bot WhatsApp: tom suave duplo (sine 698→880Hz) — "mensagem recebida" */
function tocarSomBot() {
  try {
    const ctx = new AudioContext();
    [698, 880].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = "sine";
      osc.frequency.value = freq;
      const t = i * 0.15;
      gain.gain.setValueAtTime(0.3, ctx.currentTime + t);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.12);
      osc.start(ctx.currentTime + t);
      osc.stop(ctx.currentTime + t + 0.12);
    });
  } catch {
    // AudioContext não disponível
  }
}

/** Handoff solicitado: sirene urgente 3 tons alternados (square 660↔880Hz) — atenção imediata */
function tocarSomHandoff() {
  try {
    const ctx = new AudioContext();
    const tempos = [0, 0.3, 0.6, 0.9, 1.2, 1.5];
    tempos.forEach((t, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = "square";
      osc.frequency.value = i % 2 === 0 ? 880 : 660;
      gain.gain.setValueAtTime(0.35, ctx.currentTime + t);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.25);
      osc.start(ctx.currentTime + t);
      osc.stop(ctx.currentTime + t + 0.25);
    });
  } catch {
    // AudioContext não disponível
  }
}

/** Pedido despachado: 2 tons ascendentes de confirmação (triangle 523→784Hz) */
function tocarSomDespacho() {
  try {
    const ctx = new AudioContext();
    [523, 784].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = "triangle";
      osc.frequency.value = freq;
      const t = i * 0.18;
      gain.gain.setValueAtTime(0.35, ctx.currentTime + t);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.15);
      osc.start(ctx.currentTime + t);
      osc.stop(ctx.currentTime + t + 0.15);
    });
  } catch {
    // AudioContext não disponível
  }
}

// ─── Notificação do sistema operacional ─────────────────
async function notificarSistema(titulo: string, corpo: string) {
  if (!("Notification" in window)) return;
  if (Notification.permission === "default") {
    await Notification.requestPermission();
  }
  if (Notification.permission === "granted") {
    new Notification(titulo, { body: corpo, icon: "/favicon.ico" });
  }
}

// ─── Hook principal ─────────────────────────────────────
interface UseWebSocketOptions {
  restauranteId: number | null;
  onEvento?: (evento: WsEvent) => void;
  habilitarSom?: boolean;
  habilitarNotificacaoSistema?: boolean;
}

export function useWebSocket({
  restauranteId,
  onEvento,
  habilitarSom = true,
  habilitarNotificacaoSistema = false,
}: UseWebSocketOptions) {
  const qc = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const tentativasRef = useRef(0);
  const reconectarTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const desconectadoIntencionalmente = useRef(false);

  const invalidarQueries = useCallback(
    (tipo: WsEventTipo, dados?: Record<string, unknown>) => {
      switch (tipo) {
        case "novo_pedido":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.entregasAtivas });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.diagnosticoTempo });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.mesas });
          if (habilitarSom) tocarSomNotificacao();
          if (habilitarNotificacaoSistema) {
            notificarSistema("Novo Pedido!", "Você recebeu um novo pedido.");
          }
          break;
        case "pedido_atualizado":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.entregasAtivas });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.mesas });
          break;
        case "pedido_despachado":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.entregasAtivas });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.motoboys });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.diagnosticoTempo });
          if (habilitarSom) tocarSomDespacho();
          break;
        case "pedido_cancelado":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.entregasAtivas });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.mesas });
          if (habilitarSom) tocarSomCancelamento();
          if (habilitarNotificacaoSistema) {
            notificarSistema("Pedido Cancelado", "Um pedido foi cancelado.");
          }
          break;
        case "entrega_atrasada":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.entregasAtivas });
          if (habilitarSom) tocarSomAlerta();
          if (habilitarNotificacaoSistema) {
            notificarSistema("Entrega Atrasada!", "Uma entrega ultrapassou o tempo estimado.");
          }
          break;
        case "entrega_finalizada":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.entregasAtivas });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.motoboys });
          if (habilitarSom) tocarSomDespacho();
          break;
        case "tempo_ajustado":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.configSite });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.diagnosticoTempo });
          break;
        case "mesa_paga":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.mesas });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.caixaAtual });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
          if (habilitarSom) tocarSomDespacho();
          break;
        case "motoboy_posicao":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.motoboys });
          break;
        case "tempo_medio_atualizado":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.tempoMedio });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.alertasAtraso });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.notificacoes });
          break;
        case "config_atualizada":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.config });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.configSite });
          break;
        case "printer_status":
          // Armazena status da impressora no query cache para consumo pelo Topbar
          qc.setQueryData(["printer_status"], dados ?? {});
          break;
        case "print_ack":
          // Apenas repassa via onEvento, sem invalidar queries
          break;
        case "bot_mensagem":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.botConversas });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.botDashboard });
          // Invalidar mensagens da conversa específica se estiver aberta
          if (dados?.conversa_id) {
            qc.invalidateQueries({ queryKey: ["admin", "bot", "mensagens", dados.conversa_id] });
          }
          if (habilitarSom) tocarSomBot();
          if (habilitarNotificacaoSistema) {
            const nome = dados?.nome_cliente as string || "Cliente";
            notificarSistema("WhatsApp Humanoide", `${nome} enviou uma mensagem`);
          }
          break;
        case "bot_atraso_detectado":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.botDashboard });
          if (habilitarSom) tocarSomAlerta();
          if (habilitarNotificacaoSistema) {
            const comanda = dados?.comanda as string || "";
            notificarSistema("Bot: Atraso Detectado", `Pedido #${comanda} está atrasado`);
          }
          break;
        case "bot_handoff_solicitado":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.botConversas });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.botDashboard });
          if (habilitarSom) tocarSomHandoff();
          if (habilitarNotificacaoSistema) {
            const nomeHandoff = dados?.nome_cliente as string || "Cliente";
            notificarSistema("Handoff Solicitado!", `${nomeHandoff} quer falar com um humano`);
          }
          break;
      }
    },
    [qc, habilitarSom, habilitarNotificacaoSistema]
  );

  const conectar = useCallback(() => {
    if (!restauranteId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocolo}//${host}/ws/${restauranteId}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      tentativasRef.current = 0;
    };

    ws.onmessage = (e) => {
      try {
        const evento: WsEvent = JSON.parse(e.data);
        if (evento.tipo === "ping") return;
        invalidarQueries(evento.tipo, evento.dados);
        onEvento?.(evento);
      } catch {
        // ignorar mensagens mal-formatadas
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      if (desconectadoIntencionalmente.current) return;

      // Reconexão com backoff exponencial (máx 30s)
      const delay = Math.min(1000 * 2 ** tentativasRef.current, 30000);
      tentativasRef.current += 1;
      reconectarTimeoutRef.current = setTimeout(conectar, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [restauranteId, invalidarQueries, onEvento]);

  useEffect(() => {
    desconectadoIntencionalmente.current = false;
    conectar();

    return () => {
      desconectadoIntencionalmente.current = true;
      if (reconectarTimeoutRef.current) {
        clearTimeout(reconectarTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [conectar]);

  const enviarMensagem = useCallback((msg: Record<string, unknown>): boolean => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
      return true;
    }
    return false;
  }, []);

  return { tocarSomNotificacao, tocarSomAlerta, tocarSomCancelamento, tocarSomDespacho, tocarSomBot, tocarSomHandoff, enviarMensagem };
}
