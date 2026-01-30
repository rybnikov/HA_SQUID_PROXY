
You are Codex running in **full agent mode**. Your task is to implement Release 1.3: a **React SPA** UI redesign for Squid Proxy Manager using **TailwindCSS**, based on the Figma file below.

Figma (source of truth):
https://www.figma.com/make/2uH0ood6utucyY9FC9BlLl/Squid-Proxy-Manager-Redesign?t=2mZmrstnMLgaNZrD-1

NON-NEGOTIABLE RULES
1) Follow existing repository engineering practices: TS strictness, linting, testing, modular structure, small commits.
2) Figma is authoritative: do not invent spacing/variants/layouts. Extract tokens and reuse components.
3) Home Assistant ingress-safe: routing basename, relative assets, deep link refresh support.
4) Prefer reusable primitives and composition; no one-off UI patterns.
5) No raw `fetch` outside the API client. Use TanStack Query for all server data.
6) Add/maintain unit + e2e tests for critical flows and ingress behavior.
7) If backend gaps are discovered, document them in `docs/backend-gaps.md` and implement only minimal necessary changes.

PRIMARY DELIVERABLES
A) Frontend SPA
- Vite + React + TypeScript + Tailwind
- React Router with runtime-derived basename (ingress safe)
- TanStack Query, RHF + zod
- UI primitives in `src/ui/*`
- Feature modules in `src/features/*`
- Pages + routes implemented per Figma

B) Design references and mapping
- Export primary screens and key components from Figma into `docs/figma-exports/`
- Fill `docs/figma-map.md` using `docs/FIGMA_MAP_TEMPLATE.md`
  - Map: Figma frames -> routes/pages
  - Map: Figma components -> `src/ui/*` and `src/features/*` components
  - Map: tokens -> tailwind config / CSS variables

C) Ingress & deployment correctness
- Assets resolve under ingress subpath
- Deep links + refresh work (server fallback to index.html)
- iframe-safe dialogs/menus

D) Quality gates
- Lint + typecheck pass
- Unit tests for primitives + API client + form validation
- Playwright E2E: ingress base path, dashboard renders, CRUD proxy flow, users/logs

EXECUTION SEQUENCE (do not skip)
1) Repo scan:
   - Identify existing backend endpoints, how UI is served today, and current build/deploy setup.
2) Figma scan:
   - Inventory pages/frames/components/variants
   - Export references
   - Create `docs/figma-map.md`
3) SPA scaffold:
   - Create /frontend or integrate existing structure as appropriate
   - Add toolchain, lint, tests, CI steps
4) Ingress-safe base path + asset strategy:
   - Implement runtime basename helper
   - Configure Vite base
   - Validate deep links
5) Build UI primitives from Figma:
   - Button, Card, Tabs, Dialog, DropdownMenu, Inputs, Table, Toast, Skeleton, EmptyState
6) Build domain components and pages from Figma:
   - Dashboard (proxy cards)
   - Proxy create/edit forms
   - Proxy detail tabs (overview/settings/users/logs)
7) Integrate API:
   - Typed API client, query hooks, error handling, optimistic updates if appropriate
8) Tests:
   - Unit tests + Playwright flows
9) Docs:
   - dev/build/test instructions
   - ingress notes
   - rollback instructions only if already required by repo standards (otherwise omit)

DONE CHECKLIST
- UI matches Figma for all primary screens
- Ingress safe, deep link refresh ok
- CRUD proxies ok
- Users ok
- Logs ok
- CI green (lint/typecheck/tests/build)
