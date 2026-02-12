# DevOps Engineer - Project Memory

## Environment Status (Last Verified: 2026-02-05)

### Frontend Build
- Both standalone SPA and HA panel builds work via `npm run build`
- Produces `dist/index.html` (standalone) and `dist/panel/squid-proxy-panel.js` (HA panel)
- TypeScript and ESLint checks pass cleanly

### Token Configuration (Critical)
- Container `squid-proxy-manager-local` runs with `SUPERVISOR_TOKEN=test_token`
- `run_addon_local.sh` would set `dev_token` -- known mismatch, documented in project MEMORY.md
- `setup_ha_custom_panel.sh` defaults to `test_token` -- matches the running container
- API auth: `Authorization: Bearer test_token` header required for `/api/*` endpoints
- Cookie fallback: `SUPERVISOR_TOKEN` cookie also accepted

### Port Assignments
- 8099: Addon web UI + API
- 8123: HA Core
- 3128-3160: Squid proxy instance ports
- 5173: Vite dev server (frontend hot-reload)

### Container Details
- Container name: `squid-proxy-manager-local`
- Health check: Built-in, reports "healthy"
- Source code NOT mounted (only /data volume) -- rebuild required for backend changes
- Quick iteration: `docker cp` + restart for backend files

## Auth Middleware Chain
- CORS middleware runs BEFORE auth middleware (critical ordering)
- Auth checks `Authorization: Bearer <token>` header first, then `SUPERVISOR_TOKEN` cookie
- OPTIONS requests bypass auth (CORS preflight)
- Non-API paths bypass auth entirely
