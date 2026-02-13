# Changelog

## [1.6.5] - 2026-02-13

### Changed
- **OpenVPN config patcher** moved from dedicated tab to dialog-based UI for better accessibility
- Dialog now accessible from Test Connectivity tab (Squid instances) and Connection Info tab (TLS Tunnel instances)
- Improved UX with inline error/success feedback (no window.alert() popups blocked by HA ingress)
- File upload button now uses HA-native HAButton component with styled trigger
- All HA-native components (HADialog, HACard, HAButton, HASwitch, HATextField, HASelect, HAIcon)

### Fixed
- Duplicate error message display when API patch fails
- Window.alert() blocking issues in Home Assistant iframe environment
- Component state cleanup on dialog close

## [1.6.0] - 2026-02-11

### Added
- **TLS Tunnel visual routing diagram**: Mermaid.js flowchart showing dual-destination traffic routing
- **TLS Tunnel Test tab**: Test cover site HTTPS response and VPN server TCP connectivity
- **Nginx logs endpoint**: `GET /api/instances/{name}/logs?type=nginx` for TLS Tunnel debugging
- **Built-in rate limiting**: Default 10 concurrent connections per source IP for TLS Tunnel
- **Proxy type badges**: Blue badge for Squid, green badge for TLS Tunnel on dashboard cards

### Changed
- Improved create flow with clearer descriptions for each proxy type
- Renamed "VPN Server Address" → "VPN Server Destination" for clarity
- Removed confusing "+" icons from Create Instance buttons
- FAB now only appears when instances exist (cleaner empty state)
- Mobile-responsive button layouts with proper wrapping

### Removed
- **DPI Prevention toggle** from Squid instances (feature was misleading - Squid can't defeat active DPI probes)
- Security hardening remains always-on for all Squid instances

### Fixed
- TLS Tunnel test endpoint JSON parsing error
- Dashboard FAB appearing on create page
- Button alignment issues in create flow
- Mermaid diagram rendering with proper API usage

## [1.5.6] - 2026-02-10

### Added
- **TLS Tunnel proxy type**: nginx SNI-based multiplexer for routing OpenVPN traffic through port 443 with cover website (defeats DPI port blocking, protocol signatures, and active probing)
- **DPI Prevention toggle**: per-instance setting that strips proxy-identifying headers, hides Squid version, enforces TLS 1.2+, and prefers IPv4
- **Connection Info tab**: shows OpenVPN .ovpn configuration snippet for TLS Tunnel instances
- **Cover Site tab**: manage the decoy HTTPS website served to DPI probes
- **Proxy type selector**: choose between Squid (HTTP/HTTPS proxy) and TLS Tunnel on instance creation

### Changed
- HTTPS and DPI Prevention toggles now auto-save on change (no Save button needed)
- Increased E2E test timeouts for better stability under load
- Improved process cleanup with zombie reaping and graceful SIGQUIT for nginx

### Fixed
- Stop/restart race conditions in proxy lifecycle management
- Instance cleanup between E2E tests preventing orphan process accumulation

## [1.5.5] - 2026-02-07
- Auto-restore instance states on addon restart
- Dashboard button improvements

## [1.5.4] - 2026-02-07
- Cache log highlighting, new GIFs, README + changelog

## [1.5.3] - 2026-02-07
- UI polish: HA-native button styling, icons, top-bar redesign

## [1.5.2] - 2026-02-06
- Security hardening + E2E test fixes
