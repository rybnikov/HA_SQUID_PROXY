# Figma Mapping — Release 1.3

> The Figma export assets should live under `docs/figma-exports/`.
> Update this mapping once the Figma frames and components are exported.

## 1) Screens (Frames) -> Routes

| Figma Page | Frame/Screen Name | Route | React Page Component | Notes |
|---|---|---|---|---|
| Redesign | Dashboard | / | `squid_proxy_manager/frontend/src/features/instances/DashboardPage.tsx` | Matches dashboard + modals |
| Redesign | Create Proxy | /proxies/new | `squid_proxy_manager/frontend/src/features/instances/ProxyCreatePage.tsx` | Form uses RHF + zod |
| Redesign | Proxy Details | /proxies/:name | `squid_proxy_manager/frontend/src/features/instances/ProxyDetailsPage.tsx` | Overview placeholder |
| Redesign | Settings | /settings | `squid_proxy_manager/frontend/src/features/instances/SettingsPage.tsx` | Global placeholders |

## 2) Components -> Implementation

### UI primitives (`squid_proxy_manager/frontend/src/ui/*`)
| Figma Component | Variants | React Component | Props API | Notes |
|---|---|---|---|---|
| Button | primary/secondary/ghost/danger | `Button` | `variant`, `size`, `loading` | Tailwind + CVA |
| Card | header/body/footer | `Card` | `title`, `subtitle`, `action` | |
| Badge | status | `Badge` | `tone` | |
| Input | text/password/number | `Input` | `label`, `helperText` | |
| Select | size options | `Select` | `label` | |
| Checkbox | toggle | `Checkbox` | `label` | |
| Modal | modal/dialog | `Modal` | `id`, `title`, `isOpen` | |

### Domain components (`squid_proxy_manager/frontend/src/features/**`)
| Figma Component | React Component | Feature | Notes |
|---|---|---|---|
| Proxy Card | `DashboardPage` instance card | instances | Uses `data-instance` for tests |
| Users Modal | `DashboardPage` | users | Async add/remove + error state |
| Logs Modal | `DashboardPage` | logs | Cache/access tabs |
| Settings Modal | `DashboardPage` | settings | HTTPS + cert actions |

## 3) Tokens -> Tailwind / CSS Variables

| Token Type | Figma Name | Value | Tailwind Key / CSS Var | Notes |
|---|---|---:|---|---|
| Color | Primary | TBD | `--color-primary` / `theme.colors.primary` | Update after export |
| Color | Surface | TBD | `--color-surface` / `theme.colors.surface` | Update after export |
| Text | Body | TBD | `--font-body` | Update after export |
| Radius | Card radius | TBD | `rounded-card` | Update after export |
| Shadow | Card shadow | TBD | `shadow-card` | Update after export |

## 4) Exported references
- Expected assets in `docs/figma-exports/`:
  - `dashboard.png`
  - `proxy-details.png`
  - `create-proxy.png`
  - `users.png`
  - `logs.png`
  - `settings.png`
  - `dialogs.png`
