import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: "./" so the built asset URLs are relative — the app is mounted under a
// generated path (/<appHostId~version>/...) when served from the SAP HTML5
// Application Repository / Work Zone, not at the domain root.
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
