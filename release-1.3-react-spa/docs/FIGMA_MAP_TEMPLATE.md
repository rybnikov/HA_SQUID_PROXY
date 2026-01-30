
# Figma Mapping — Template

> Copy to `docs/figma-map.md` and fill in after exporting from Figma.

## 1) Screens (Frames) -> Routes

| Figma Page | Frame/Screen Name | Route | React Page Component | Notes |
|---|---|---|---|---|
|  | Dashboard | / | `src/pages/DashboardPage.tsx` | |
|  | Create Proxy | /proxies/new | `src/pages/ProxyCreatePage.tsx` | |
|  | Proxy Details | /proxies/:id | `src/pages/ProxyDetailsPage.tsx` | Tabs: Overview/Settings/Users/Logs |
|  | Global Settings (if any) | /settings | `src/pages/SettingsPage.tsx` | |

## 2) Components -> Implementation

### UI primitives (`src/ui/*`)
| Figma Component | Variants | React Component | Props API | Notes |
|---|---|---|---|---|
| Button | primary/secondary/ghost/danger, sizes | `ui/Button.tsx` | `variant`, `size`, `loading` | |
| Card | header/body/footer | `ui/Card.tsx` | slots | |
| Tabs | ... | `ui/Tabs.tsx` | items, value, onChange | |
| Dialog | confirm/form | `ui/Dialog.tsx` | open, onOpenChange | |
| Dropdown Menu | ... | `ui/DropdownMenu.tsx` | items | |
| Input | ... | `ui/Input.tsx` | RHF-compatible | |

### Domain components (`src/features/**/components`)
| Figma Component | React Component | Feature | Notes |
|---|---|---|---|
| Proxy Card | `features/proxies/components/ProxyCard.tsx` | proxies | |
| Users Table | `features/users/components/UsersTable.tsx` | users | |
| Logs Viewer | `features/logs/components/LogsViewer.tsx` | logs | |

## 3) Tokens -> Tailwind / CSS Variables

| Token Type | Figma Name | Value | Tailwind Key / CSS Var | Notes |
|---|---|---:|---|---|
| Color | Primary |  | `--color-primary` / `theme.colors.primary` | |
| Color | Surface |  | `--color-surface` / `theme.colors.surface` | |
| Text | Body |  | `text-sm` mapping | |
| Radius | Card radius |  | `rounded-lg` or custom | |
| Shadow | Card shadow |  | `shadow-sm` mapping | |

## 4) Exported references
- Store images in `docs/figma-exports/` with naming:
  - `dashboard.png`
  - `proxy-details.png`
  - `create-proxy.png`
  - `users.png`
  - `logs.png`
  - `dialogs.png`
- Store SVG icons in `src/assets/icons/` (if required)
