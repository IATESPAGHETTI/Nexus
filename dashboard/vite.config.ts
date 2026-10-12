import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// NEXUS dashboard — pure renderer of backend/ state (see dashboard/CLAUDE.md).
// Proxies /api to the FastAPI backend so the dev server and backend/ stay on
// separate processes/ports, matching the rest of NEXUS's process isolation.
// Phase 10: `npm run preview` (serves the real production `dist/` build,
// bundled into 2 files instead of dev mode's ~100+ unbundled module
// requests -- see docs/PROJECT_STATE.md's startup-performance note) needs
// the same /api proxy as the dev server, or it can't reach backend/ either.
// Optional approval gate: if NEXUS_APPROVER_TOKEN is set in the environment that starts the
// dev server, the proxy attaches it to every backend call (server-side only, never in the
// browser bundle). The backend then refuses approvals that do not carry it.
const APPROVER_TOKEN = process.env.NEXUS_APPROVER_TOKEN
const API_PROXY = {
  target: 'http://127.0.0.1:8000',
  changeOrigin: true,
  rewrite: (path: string) => path.replace(/^\/api/, ''),
  ...(APPROVER_TOKEN ? { headers: { 'X-Approver-Token': APPROVER_TOKEN } } : {}),
}

// Presentation page: the demo sends real GET /orders requests to the simulated
// production service so an injected fault is actually observable (see
// dashboard/src/api/client.ts sendCustomerRequests). Deliberately narrow:
// only GET /production/orders[/<id>] is forwarded — production's /admin/*
// control plane is never reachable through this proxy.
const PRODUCTION_TRAFFIC_PROXY = {
  target: 'http://127.0.0.1:8001',
  changeOrigin: true,
  rewrite: (path: string) => path.replace(/^\/production/, ''),
  bypass: (req: { url?: string; method?: string }) => {
    const path = (req.url ?? '').split('?')[0]
    const allowed = req.method === 'GET' && /^\/production\/orders(\/\d+)?$/.test(path)
    return allowed ? undefined : false
  },
}

const PROXY = { '/api': API_PROXY, '/production': PRODUCTION_TRAFFIC_PROXY }

export default defineConfig({
  plugins: [react()],
  // Optional: two dev servers that share one node_modules (e.g. a git worktree linked to the main
  // checkout) overwrite each other's dependency cache and break React. Give one its own folder.
  ...(process.env.NEXUS_VITE_CACHE ? { cacheDir: process.env.NEXUS_VITE_CACHE } : {}),
  server: {
    port: 5173,
    proxy: PROXY,
  },
  preview: {
    port: 4173,
    proxy: PROXY,
  },
})
