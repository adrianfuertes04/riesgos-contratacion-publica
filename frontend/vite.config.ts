import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo, /api se redirige a la API FastAPI local. Se usa 127.0.0.1 y no "localhost"
// porque Node 18 resuelve "localhost" a IPv6 (::1) y uvicorn escucha en IPv4.
export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 750,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          echarts: ["echarts/core", "echarts/charts", "echarts/components", "echarts/renderers"],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.VITE_API_URL ?? "http://127.0.0.1:8000",
    },
  },
});
