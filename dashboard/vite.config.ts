import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// NEXUS dashboard — pure renderer of backend/ state (see dashboard/CLAUDE.md).
// Proxies /api to the FastAPI backend so the dev server and backend/ stay on
// separate processes/ports, matching the rest of NEXUS's process isolation.
// Phase 10: `npm run preview` (serves the real production `dist/` build,
// bundled into 2 files instead of dev mode's ~100+ unbundled module
// requests -- see docs/PROJECT_STATE.md's startup-performance note) needs
// the same /api proxy as the dev server, or it can't reach backend/ either.
const API_PROXY = {
  target: 'http://127.0.0.1:8000',
  changeOrigin: true,
  rewrite: (path: string) => path.replace(/^\/api/, ''),
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
  server: {
    port: 5173,
    proxy: PROXY,
  },
  preview: {
    port: 4173,
    proxy: PROXY,
  },
})
