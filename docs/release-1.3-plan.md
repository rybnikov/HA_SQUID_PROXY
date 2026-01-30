# Release 1.3 Execution Plan — React SPA + Docker-First Workflow

## Goals
- Replace legacy inline HTML with a React + Tailwind SPA that matches Figma designs.
- Enforce architecture + quality rules from `release-1.3-react-spa/docs/README.md`.
- Keep tests and dev workflows Docker-first (linting can remain local).
- Maintain HA ingress compatibility and deep-link resilience.

## Scope
1. **Frontend scaffold (React + Vite + Tailwind 4 + TS)**
2. **Reusable UI primitives and feature components**
3. **Dashboard + CRUD flows (instances, users, logs, settings, test, delete)**
4. **Ingress-safe routing and asset resolution**
5. **Docker build integration**
6. **Test coverage in Docker**
7. **Docs + Figma exports**

## Execution Steps
1. **Figma mapping and export placeholders**
   - Create `docs/figma-exports/` and `docs/figma-map.md` (based on template).
   - Commit exported screenshots once available.

2. **React SPA scaffold**
   - `squid_proxy_manager/frontend` with Vite 7 + React 19 + Tailwind 4 + TS strict.
   - Configure `@tailwindcss/vite` + `tailwind.config.ts` with token-based CSS variables.
   - Add router + ingress basename helper from samples.

3. **UI primitives and features**
   - `ui/*` primitives: Button, Card, Badge, Modal, Input.
   - `features/instances` + `features/users` + `features/logs`.
   - Avoid business logic in JSX; keep in hooks/services.

4. **API + data layer**
   - Central `api/client.ts` using `fetch` + token injection.
   - TanStack Query for server state and mutations.
   - Ensure `window.apiFetch` compatibility for e2e tests.

5. **Backend SPA serving**
   - Serve SPA from `/app/static` with `index.html` fallback.
   - Inject `SUPERVISOR_TOKEN` into HTML.
   - Add `/assets` static route and catch-all route for deep links.

6. **Docker-first workflow**
   - Add `tests/Dockerfile.frontend` and docker-compose profile for frontend tests.
   - Extend `run_tests.sh` with `ui` and include in `all`.
   - CI job to run frontend tests/typecheck/build in Docker.

7. **Test coverage**
   - Unit tests for UI primitives and API client (Vitest).
   - Update E2E selectors to new UI structure while keeping functional parity.

8. **Versioning + docs**
   - Bump to `1.3.0` in `config.yaml`, Docker labels, API response.
   - Update `DEVELOPMENT.md` with Docker-first frontend workflows.

## Definition of Done
- React SPA served by backend, works under ingress.
- UI interactions cover create/start/stop/settings/logs/users/test/delete flows.
- Docker-based tests pass: unit/integration/e2e + frontend tests.
- CI runs frontend test job in Docker.
- Figma export placeholders committed and ready for assets.
