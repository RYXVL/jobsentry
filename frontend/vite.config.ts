/**
 * Vite config.
 *
 * In development the frontend runs on http://localhost:5173 and forwards every
 * request starting with /api to the FastAPI backend, so the browser only ever
 * talks to one origin. Change the backend address with JOBSENTRY_API_URL in
 * frontend/.env (see .env.example).
 */
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // "" loads every variable, not just VITE_*. These are only used here,
  // in the dev server, and are never exposed to browser code.
  const env = loadEnv(mode, ".", "");
  const apiTarget = env.JOBSENTRY_API_URL || "http://127.0.0.1:8000";
  const proxy = { "/api": { target: apiTarget, changeOrigin: true } };

  return {
    plugins: [react()],
    server: { port: 5173, proxy },
    preview: { port: 4173, proxy },
  };
});
