import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "food.derekh.entregador",
  appName: "Derekh Entregador",
  webDir: "dist",
  server: {
    androidScheme: "https",
    // Em produção, servir assets locais do APK
    // Em dev, descomentar para usar server externo:
    // url: "http://192.168.1.X:5174",
  },
  plugins: {
    Geolocation: {
      // Solicitar permissão de localização em background automaticamente
    },
    App: {
      // Controle de ciclo de vida do app
    },
  },
  android: {
    backgroundColor: "#0a0a0a",
    allowMixedContent: false,
    captureInput: true,
    webContentsDebuggingEnabled: true,
  },
};

export default config;
