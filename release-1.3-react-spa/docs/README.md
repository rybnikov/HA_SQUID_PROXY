
# Squid Proxy Manager — Release 1.3 (React SPA)

This archive is designed for **Codex full agent mode** to implement the React SPA UI redesign from Figma.

**Intentionally excluded:**
- Feature rollout plans
- Migration strategies/tasks
- Time estimates

---

## Design Source of Truth (Figma)
Figma file:
https://www.figma.com/make/2uH0ood6utucyY9FC9BlLl/Squid-Proxy-Manager-Redesign?t=2mZmrstnMLgaNZrD-1

Codex MUST:
- Treat Figma as authoritative for spacing, hierarchy, variants, and layout behavior
- Export design references and commit them (`docs/figma-exports/`)
- Build reusable components matching Figma components before building pages

---

## Mandatory Engineering Practices
Follow repository engineering standards (do not “prototype” your way into the codebase).

### Code quality
- TypeScript everywhere (no `any`, no implicit `any`)
- ESLint + Prettier enforced
- Strict lint + typecheck in CI
- No dead code / unused exports

### Architecture
- Feature-oriented modules under `features/*`
- Stateless UI primitives under `ui/*`
- Domain logic isolated from presentation
- No business logic inside JSX render blocks

### Styling
- TailwindCSS only
- No inline styles
- No arbitrary values unless explicitly derived from Figma tokens
- Tokens extracted from Figma into Tailwind theme extension and/or CSS variables

### State & data
- TanStack Query for server state
- No raw `fetch` outside API client
- Consistent loading / error / empty states

### Testing
- Unit tests: UI primitives, API client, forms/validation
- E2E (Playwright): ingress routing, dashboard, CRUD proxy flow, users/logs

### Home Assistant / Ingress
- Works under ingress subpath
- No absolute asset paths
- Deep-link refresh must not 404
- iframe-safe rendering

---

## Included materials
- `docs/CODEX_SYSTEM_PROMPT.md` — drop-in prompt for Codex full-agent mode
- `docs/FIGMA_MAP_TEMPLATE.md` — mapping tables to fill from Figma export
- `docs/INGRESS.md` — ingress-safe routing + assets guidance
- `samples/` — reusable code samples (extend these, do not rewrite)
