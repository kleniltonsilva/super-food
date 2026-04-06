import { useEffect, useState } from "react";

interface SplashScreenProps {
  onFinish: () => void;
  duration?: number;
}

export default function SplashScreen({ onFinish, duration = 2000 }: SplashScreenProps) {
  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    const fadeTimer = setTimeout(() => setFadeOut(true), duration - 400);
    const finishTimer = setTimeout(onFinish, duration);
    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(finishTimer);
    };
  }, [onFinish, duration]);

  return (
    <div
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-[#0a0a0a] transition-opacity duration-400 ${
        fadeOut ? "opacity-0" : "opacity-100"
      }`}
    >
      {/* Logo com animação de entrada */}
      <img
        src="/derekh-motoboy-icon.png"
        alt="Derekh Food"
        className="h-32 w-32 animate-[splash-logo_0.8s_ease-out_both]"
      />

      {/* Nome do app */}
      <h1 className="mt-4 animate-[splash-text_0.8s_ease-out_0.3s_both] text-xl font-bold text-white">
        Derekh Entregador
      </h1>

      {/* Barra de loading sutil */}
      <div className="mt-8 h-0.5 w-24 overflow-hidden rounded-full bg-gray-800">
        <div
          className="h-full rounded-full bg-green-500"
          style={{
            animation: `splash-bar ${duration - 400}ms ease-in-out forwards`,
          }}
        />
      </div>

      <style>{`
        @keyframes splash-logo {
          0% { opacity: 0; transform: scale(0.5); }
          100% { opacity: 1; transform: scale(1); }
        }
        @keyframes splash-text {
          0% { opacity: 0; transform: translateY(10px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes splash-bar {
          0% { width: 0%; }
          100% { width: 100%; }
        }
      `}</style>
    </div>
  );
}
