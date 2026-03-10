import { useCallback, useRef } from "react";

export function useNotificacaoSonora() {
  const audioCtxRef = useRef<AudioContext | null>(null);

  const tocar = useCallback(() => {
    try {
      if (!audioCtxRef.current) {
        audioCtxRef.current = new AudioContext();
      }
      const ctx = audioCtxRef.current;

      // 3 beeps rápidos (880Hz)
      for (let i = 0; i < 3; i++) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = "sine";
        osc.frequency.value = 880;
        gain.gain.value = 0.3;
        const start = ctx.currentTime + i * 0.5;
        osc.start(start);
        osc.stop(start + 0.4);
      }

      // Vibração
      if (navigator.vibrate) {
        navigator.vibrate([200, 100, 200, 100, 300]);
      }

      // Notificação do sistema
      if ("Notification" in window && Notification.permission === "granted") {
        new Notification("Nova entrega!", {
          body: "Você tem uma nova entrega atribuída",
          icon: "/icons/icon-192.png",
          requireInteraction: true,
        });
      }
    } catch {
      // Audio bloqueado pelo browser, ignorar
    }
  }, []);

  const pedirPermissao = useCallback(async () => {
    if ("Notification" in window && Notification.permission === "default") {
      await Notification.requestPermission();
    }
  }, []);

  return { tocar, pedirPermissao };
}
