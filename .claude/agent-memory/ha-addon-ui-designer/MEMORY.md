# HA Addon UI Designer - Agent Memory

## Key Patterns Discovered

### Top Bar Status + Action Controls (InstanceSettingsPage)
- Use a **single toggle button** pattern (Start when stopped, Stop when running) instead of two buttons where one is always disabled
- This mirrors HA's own addon detail page pattern and the DashboardPage card pattern (lines 276-300)
- Pair with a **status chip** (pill with dot + label) for at-a-glance status
- Status chip: `border-radius: 16px`, tinted background (`rgba(67,160,71,0.15)` for running, `rgba(158,158,158,0.12)` for stopped), 8px dot, 12px/500 label
- Stop button uses `outlined` variant (lighter weight for destructive actions), Start uses filled `success` variant

### HA CSS Custom Properties Used
- `--success-color` (#43a047) - running status, start actions
- `--error-color` (#db4437) - danger zone, stop actions, delete
- `--secondary-text-color` (#9b9b9b) - stopped status, helper text
- `--primary-text-color` (#e1e1e1) - main text
- `--primary-color` (#009ac7) - brand/accent, port labels
- `--card-background-color` (#1c1c1c) - card backgrounds
- `--divider-color` (rgba(225,225,225,0.12)) - borders
- `--app-header-background-color` (#1c1c1c) - top bar background

### Component Wrappers (src/ui/ha-wrappers/)
- HAButton: supports `variant` (primary/secondary/ghost/danger/success), `size` (sm/md/lg), `outlined`, `loading`
- HAIconButton: icon-only buttons, has fallback rendering for non-HA environments
- HAStatusDot: simple dot+label component (now unused in settings page top bar)
- HAIcon: renders `<ha-icon>` natively or fallback unicode chars
- HATopBar: `title`, `subtitle`, `onBack`, `actions` (ReactNode slot)
- HACard: `title`, `outlined` props
- HADialog: custom modal (required for HA ingress - NO window.confirm/alert)

### Frontend Build & Deploy
- Production build: `npm run build` in `squid_proxy_manager/frontend/`
- Panel JS served from `/app/static/panel/squid-proxy-panel.js` inside addon container
- To hot-update running container: `docker cp dist/panel/squid-proxy-panel.js ha_squid_proxy-addon-1:/app/static/panel/`
- HA aggressively caches panel JS - need `ignoreCache: true` reload + cache clear
- The `ha-button` native element is available inside HA ingress (customElements check)

### Data-Testid Conventions
- `settings-start-button` - start action in settings top bar
- `settings-stop-button` - stop action in settings top bar
- `settings-status-chip` - status indicator chip in settings top bar
- `settings-delete-button` - delete in danger zone
- `settings-view-logs-button` - logs button
- `delete-confirm-button` - confirm in delete dialog
- `instance-card-{name}` - dashboard cards
- `instance-start-chip-{name}` / `instance-stop-chip-{name}` - dashboard card actions

### DashboardPage Card Pattern
- Icon area with status-colored rounded background (12px radius, 40x40)
- Green overlay dot for running instances (absolute positioned)
- Bottom section with port info + single toggle icon button
- Already uses the single-button toggle pattern (only show relevant action)

### Critical HA Ingress Rules
- NEVER use window.confirm/alert/prompt - blocked in iframe
- Always use HADialog for confirmations
- Panel JS loaded via HA panel registration at `/panel/squid-proxy-panel.js`
