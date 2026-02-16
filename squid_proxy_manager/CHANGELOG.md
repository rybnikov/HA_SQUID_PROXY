# Changelog

## 1.6.8

### Fixed
- Click-to-browse in OpenVPN patcher dialog now works in HA ingress iframe (replaced JS `.click()` with native `<label>` association)
- OpenVPN patching blocked for TLS tunnel when external IP is not configured (prevents useless `localhost` in patched config)

### Added
- External address and client port displayed in TLS tunnel Connection Info tab
- Syntax highlighting for raw config editor (nginx/squid keywords, comments, strings, numbers)

### Changed
- TLS tunnel OpenVPN patcher shows error (red) instead of warning (orange) when external IP is missing

### Removed
- Dead OpenVPNTab.tsx (replaced by OpenVPNPatcherDialog.tsx in v1.6.5)

## 1.5.5

- Persist instance desired state (running/stopped) across addon restarts
- Dashboard start/stop buttons now show icon + text instead of icon-only
- All stop/delete buttons use danger variant, start buttons use success variant

## 1.5.4

- Add syntax highlighting for cache/debug logs (timestamps, severity levels, kid processes)
- Update addon marketplace README with GIF demos and feature documentation
- Add changelog for addon marketplace visibility

## 1.5.3

- Fix HA-native button styling: use `appearance` attribute (plain/accent/outlined) for proper rendering
- Add MDI icons to all action buttons (Save, Add User, Delete, Test, View Logs, etc.)
- Redesign instance settings top-bar: status chip + single toggle Start/Stop button
- Fix HACard style merge bug where parent styles overwrote base styles
- Change stopped status indicator from red to neutral gray

## 1.5.2

- Security hardening across backend and frontend
- E2E test fixes for improved CI reliability

## 1.5.1

- Fix HA ingress: escape iframe for native web components
- Bump version

## 1.5.0

- Complete frontend redesign with Home Assistant native web components
- Route-based navigation (dashboard, create, settings pages)
- React 19 + TypeScript + Vite + Tailwind CSS
- HA ingress integration with custom panel
- Multiple proxy instance management via web UI
- HTTPS certificate generation and management
- Basic authentication with per-instance user management
- Proxy connectivity testing from the UI
- Access and cache log viewer with search and auto-refresh
- Unified Docker Compose dev setup with HA Core
- Fully dockerized GIF recording for documentation
