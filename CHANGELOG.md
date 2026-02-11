# Changelog

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
