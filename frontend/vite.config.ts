import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.png", "brand/*.png"],
      manifest: {
        name: "MultiLife · Recepção",
        short_name: "Recepção",
        description: "Totem de autoatendimento da recepção MultiLife",
        lang: "pt-BR",
        start_url: "/totem",
        display: "fullscreen",
        orientation: "any",
        background_color: "#ffffff",
        theme_color: "#164F95",
        icons: [
          { src: "/pwa-192.png", sizes: "192x192", type: "image/png" },
          { src: "/pwa-512.png", sizes: "512x512", type: "image/png", purpose: "any maskable" },
        ],
      },
      workbox: {
        navigateFallback: "/index.html",
        globPatterns: ["**/*.{js,css,html,png,woff2}"],
        // Nunca cachear a API: o totem precisa sempre falar com o SGG "ao vivo".
        runtimeCaching: [{ urlPattern: /\/(totem|admin|health)(\/|$)/, handler: "NetworkOnly" }],
      },
    }),
  ],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { port: Number(process.env.PORT) || 5173, host: true, strictPort: false },
});
