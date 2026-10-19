import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api/* is proxied to FastAPI so the browser only ever talks to one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
