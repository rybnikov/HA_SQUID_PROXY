# Release Notes - Version 1.6.0

## 🎉 Major UX Rework: DPI Prevention & TLS Tunnel Improvements

This release removes the misleading DPI prevention toggle and introduces proper DPI evasion guidance, improved UI/UX, and new testing capabilities for TLS Tunnel instances.

---

## 🔥 Breaking Changes

- **Removed DPI Prevention Toggle** from Squid instances (feature was misleading - Squid's passive countermeasures don't defeat active DPI probes)
- Existing instances with `dpi_prevention` setting will continue to work (backward compatible), but the toggle is no longer shown in the UI

---

## ✨ New Features

### TLS Tunnel Enhancements

1. **Visual Routing Diagram** (Mermaid.js)
   - Beautiful flowchart showing how TLS Tunnel routes traffic
   - Color-coded nodes for easy understanding
   - Mobile-responsive design

2. **Test Tab for TLS Tunnel**
   - **Test Cover Site**: Verify DPI probes see the cover website
   - **Test VPN Forwarding**: Check TCP connectivity to VPN server
   - Real-time test results with detailed error messages

3. **Nginx Logs**
   - New endpoint: `GET /api/instances/{name}/logs?type=nginx`
   - View nginx error logs for TLS Tunnel instances
   - Helps debug routing and certificate issues

4. **Built-in Rate Limiting**
   - Default: 10 concurrent connections per source IP
   - Configurable via API
   - Prevents abuse and resource exhaustion

### UI/UX Improvements

1. **Proxy Type Badges**
   - 🔵 **Squid Proxy** (blue badge)
   - 🟢 **TLS Tunnel** (green badge)
   - Instantly identify proxy type on dashboard

2. **Improved Create Flow**
   - Better descriptions for each proxy type
   - Clear explanation of TLS Tunnel dual-destination behavior
   - Renamed "VPN Server Address" → "VPN Server Destination" for clarity

3. **Button Consistency**
   - Removed confusing "+" icons from Create buttons
   - Fixed button alignment issues
   - FAB only shows when instances exist (cleaner empty state)

4. **Mobile-First Design**
   - Responsive layouts tested on mobile devices
   - Proper button wrapping on small screens
   - Full-width inputs and search bars

---

## 🐛 Bug Fixes

- Fixed TLS Tunnel test endpoint JSON parsing error
- Fixed dashboard FAB appearing on create page
- Corrected response format mapping for test results
- Improved Mermaid diagram rendering with proper API usage

---

## 📝 Backend Changes

### Removed
- `dpi_prevention` parameter from all create/update endpoints
- DPI prevention config block from squid_config.py (security hardening remains always-on)

### Added
- `POST /api/instances/{name}/test-tunnel` - Test TLS Tunnel connectivity
  - `test_type: "cover_site"` - Test cover website HTTPS response
  - `test_type: "vpn_forward"` - Test TCP connectivity to VPN server
- `GET /api/instances/{name}/logs?type=nginx` - Fetch nginx logs for TLS Tunnel
- Rate limiting directives in TLS Tunnel nginx config (`limit_conn_zone`, `limit_conn`)

---

## 🎨 Frontend Changes

### Added
- `MermaidDiagram` component for rendering UML diagrams
- `TlsTunnelTestTab` - New test tab for TLS Tunnel instances
- Proxy type badges on dashboard cards
- Empty state "Create Instance" button (no FAB on empty dashboard)

### Modified
- `ProxyCreatePage` - Mermaid diagram, improved descriptions, removed DPI toggle
- `DashboardPage` - Conditional FAB rendering, proxy type badges, removed + icons
- `GeneralTab` - Removed DPI prevention toggle

### Removed
- DPI prevention UI components and state management
- Confusing "+" icons from action buttons

---

## 📦 Dependencies

### Added
- `mermaid@^11.0.0` - For rendering UML diagrams

---

## 🧪 Testing

- ✅ All unit tests passing (195 tests)
- ✅ All integration tests passing
- ✅ E2E tests updated for new UI
- ✅ New E2E tests added:
  - `test_proxy_type_badges_visible`
  - `test_no_dpi_toggle_for_squid`
  - `test_tls_tunnel_routing_diagram_visible`
  - `test_tls_tunnel_field_labels`
  - `test_tls_tunnel_test_tab_exists`
  - `test_tls_tunnel_nginx_logs_tab`
  - `test_squid_instance_no_test_tab`
  - `test_rate_limiting_default_value`

---

## 📚 Documentation Updates

- Updated README with TLS Tunnel test tab documentation
- Added migration guide for DPI prevention removal
- New GIF recordings demonstrating:
  - TLS Tunnel creation with routing diagram
  - Proxy type badges on dashboard
  - TLS Tunnel test functionality

---

## 🔄 Migration Guide

### For Users with DPI Prevention Enabled

The DPI prevention toggle has been removed because:
- Squid's DPI countermeasures only defend against **passive** DPI
- Active DPI probes can still detect Squid by connecting to it
- **TLS Tunnel is the correct tool for DPI evasion** (serves real HTTPS website to probes)

**What happens to existing instances?**
- Squid security hardening (header stripping, version hiding) remains **always-on**
- The `dpi_prevention` setting in `instance.json` is ignored but preserved
- No action required - your instances continue working

**Recommended Action:**
If you need DPI evasion, create a **TLS Tunnel** instance instead:
1. Select "TLS Tunnel" proxy type
2. Configure VPN server destination
3. Optionally set cover domain for SSL certificate
4. Use the Test tab to verify routing works correctly

---

## 🙏 Credits

- Mermaid.js team for the excellent diagram rendering library
- Home Assistant community for feedback and testing
- All contributors who reported UI/UX issues

---

## 📅 Release Date

**February 11, 2026**

## 🔗 Links

- [GitHub Repository](https://github.com/rybnikov/HA_SQUID_PROXY)
- [Documentation](https://github.com/rybnikov/HA_SQUID_PROXY/blob/main/README.md)
- [Issue Tracker](https://github.com/rybnikov/HA_SQUID_PROXY/issues)
