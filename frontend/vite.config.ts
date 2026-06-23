import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "./",
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        // Keep the static Pages bundle cache-friendly without changing app behavior.
        manualChunks: {
          react: ["react", "react-dom"],
          charts: ["echarts", "echarts-for-react"],
          icons: ["lucide-react"]
        }
      }
    }
  },
  server: {
    port: 5173
  }
});
