# UI Builder Agent Memory

## Design Tokens & CSS Custom Properties
- Card background: `var(--card-background-color, #1c1c1c)`
- Primary text: `var(--primary-text-color, #e1e1e1)`
- Secondary text: `var(--secondary-text-color, #9b9b9b)`
- Divider: `var(--divider-color, rgba(225,225,225,0.12))`
- Primary accent: `var(--primary-color, #009ac7)` (blue)
- Success: `var(--success-color, #43a047)` (green)
- Error: `var(--error-color, #db4437)` (red)
- Header bg: `var(--app-header-background-color, #1c1c1c)`

## Component Patterns

### HAButton
- `ha-button` uses `--mdc-theme-primary` for text/border color
- Cast style as `CSSProperties` for CSS custom props
- Variants: primary (raised), secondary (outlined), ghost, danger, success

### HACard
- Fallback: 12px border-radius, 1px outlined border, card-background-color bg
- Has `statusTone` prop: 'loaded' | 'not_loaded' | 'error'

### HATopBar
- 56px min-height, flex layout, divider-color bottom border
- Props: title, subtitle, onBack, actions

### HAIconButton
- Fallback: 40x40px, 20px font, 8px padding, no bg, 50% border-radius
- Icon fallback map includes: arrow-left, cog, play, stop, server-network, chevron-right

### HAStatusDot
- running: green, stopped: red (NOT gray), error: red

### HAFab
- Fixed bottom-right (24px inset), wraps HAButton raised primary

## Dashboard Card Design (v2 - HA integration style)
- Top section: clickable row with icon area (40x40, 12px radius, status-tinted bg), instance name, chevron-right
- Green dot overlay (12px, absolute top-right of icon area) when running
- Divider: 1px, 0 16px horizontal margin
- Bottom section: port info in primary-color, single play OR stop HAIconButton (show only relevant action, not both)
- Grid: `repeat(auto-fill, minmax(min(100%, 350px), 1fr))`, 16px gap
- Search bar: pill-shaped (28px radius), magnify icon prefix, full-width, shown only when instances exist
- FAB replaces top bar "Add Instance" button

## Data-testid Attributes (CRITICAL - E2E selectors)
- `instance-card-{name}` on HACard wrapper
- `instance-settings-chip-{name}` on clickable card top section (navigates to settings)
- `instance-start-chip-{name}` on Start icon button
- `instance-stop-chip-{name}` on Stop icon button
- `add-instance-button` on HAFab (was on top bar button)
- `empty-state-add-button` on empty state CTA
- `dashboard-search-input` on search input (new)

## Create Page Design (v2 - minimalistic buttons)
- ONE primary/raised blue button per page (Create Instance), all others ghost or outlined
- Bottom button row: Cancel (ghost, left) + Create Instance (raised, right) with `space-between`
- HAIcon with `slot="icon"` inside HAButton for icon+text buttons
- Remove buttons in user list: HAIconButton (mdi:close) instead of text HAButton
- Add User: secondary (outlined) with mdi:account-plus icon

## HAIcon Fallback Notes
- HAIcon and HAIconButton have SEPARATE fallback maps
- mdi:account-plus added to HAIcon by linter/teammate (maps to unicode plus sign)

## Resolved Issues
- HTTPSTab.tsx unused HAIcon import: resolved (icon now used for mdi:certificate)

## Settings Page Design (v2 - minimalistic buttons + logs dialog)
- Buttons with icons: use `<HAIcon icon="mdi:..." slot="icon" />` inside HAButton
- Logs moved from inline HACard to HADialog (maxWidth="900px", 60vh height content, padding: 0 16px 16px)
- LogsTab unchanged, fills dialog height via flex
- Instance Logs card: row layout with title/description left, "View Logs" button right
- Danger Zone: card with red left border, no title prop. Flex row layout (title+description left, outlined danger delete button right, gap 16px)
- Delete Instance button: `variant="danger" outlined` with mdi:delete icon
- Delete confirm dialog: `variant="danger" outlined` (not raised)
- User delete confirm dialog: `variant="danger" outlined`
- Start/Stop in HATopBar actions: SEPARATE HAIconButton (mdi:play + mdi:stop) + HAStatusDot, gap 4px
- HADialog supports `maxWidth` prop (defaults '500px')

## Settings Page Test IDs
- `settings-tabs` on Configuration HACard
- `settings-start-button` on play HAIconButton in top bar
- `settings-stop-button` on stop HAIconButton in top bar
- `settings-view-logs-button` on View Logs HAButton
- `settings-delete-button` on Delete HAButton in danger zone
- `delete-confirm-button` on Delete HAButton in confirm dialog

## Build Commands
- `npm run typecheck` (tsc --noEmit)
- `npm run lint` (eslint)
- `npm run test -- --run` (vitest)
- `npm run build` builds both standalone and panel configs
