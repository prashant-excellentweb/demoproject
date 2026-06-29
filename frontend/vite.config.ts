import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": "/src" },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:9000", changeOrigin: true },
      "/media": { target: "http://127.0.0.1:9000", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:9000", ws: true },
    },
  },
});
