# SDET Test Engineer Memory

## Test Infrastructure

### Frontend Tests
- **Framework**: Vitest v4.0.18 with `@testing-library/react`
- **Test files**: `src/tests/` directory (4 test files, 30 tests total)
  - `apiClient.test.ts` (2 tests) - API client unit tests
  - `validation.test.ts` (13 tests) - Input validation tests (incl TLS tunnel)
  - `haWrappers.test.tsx` (4 tests) - HA wrapper component tests
  - `mockMode.test.ts` (11 tests) - Mock API mode tests (incl TLS tunnel)
- **Run command**: `npm run test -- --run`
- **Duration**: ~8 seconds total

### Key Patterns
- HA wrapper tests use `fireEvent` from testing-library
- HASwitch test mocks `customElements.get` to force fallback rendering
- Mock mode tests use timer delays (~300-1500ms) to simulate API latency
- MockApiClient mutates shared state; create fresh instance per describe block

### Backend Test Patterns
- Integration `conftest.py` patches: DATA_DIR, CONFIG_DIR, CERTS_DIR, LOGS_DIR, SQUID_BINARY, NGINX_BINARY
- `call_handler()` in test_helpers.py calls handlers without binding ports (avoids macOS PermissionError)
- Routes must be manually registered in conftest fixture (no autodiscovery)
- Unit tests patch `proxy_manager.*` constants directly
- Both `squid_installed` and `nginx_installed` are session-scoped fixtures providing fake binaries

### TLS Tunnel Testing
- proxy_type: 'squid' | 'tls_tunnel' (VALID_PROXY_TYPES)
- tls_tunnel uses nginx binary, stop sends SIGQUIT (not SIGTERM)
- tls_tunnel instances have nginx_stream.conf + nginx_cover.conf (not squid.conf)
- User management endpoints return 400 for tls_tunnel (checked by _check_squid_type)
- Missing proxy_type defaults to "squid" (backward compat)
- cover_site_port = port + 10000 (with fallback if >65535)
- New test files: test_tls_tunnel_config.py, test_proxy_manager_tls.py, test_tls_tunnel_api.py

## Fixed Issues

### HADialog Test Update (2026-02-05)
- **Problem**: `HADialog` was rewritten from native `<ha-dialog>` web component to pure HTML/CSS overlay
- **Root cause**: Old test fired `CustomEvent('closed')` which native ha-dialog emitted; new impl uses backdrop click + Escape key
- **Fix**: Changed test from `fireEvent(dialog!, new CustomEvent('closed'))` to `fireEvent.click(dialog!)` to test backdrop click
- **File**: `src/tests/haWrappers.test.tsx` line 56-68

## data-testid Coverage (Frontend Source)

- `instance-card-{name}` -> DashboardPage.tsx:99
- `instance-start-chip-{name}` -> DashboardPage.tsx:157
- `instance-stop-chip-{name}` -> DashboardPage.tsx:166
- `instance-settings-chip-{name}` -> DashboardPage.tsx:174
- `add-instance-button` -> DashboardPage.tsx:54, 189
- `create-name-input` -> ProxyCreatePage.tsx:112
- `create-port-input` -> ProxyCreatePage.tsx:125
- `create-https-switch` -> ProxyCreatePage.tsx:135
- `create-submit-button` -> ProxyCreatePage.tsx:213
- `settings-delete-button` -> InstanceSettingsPage.tsx:144
- `delete-confirm-button` -> InstanceSettingsPage.tsx:165
- `settings-https-switch` -> GeneralTab.tsx:65
- `settings-save-button` -> GeneralTab.tsx:73
- `cert-regenerate-button` -> HTTPSTab.tsx:83
- `logs-viewer` -> LogsTab.tsx:117
- `user-list` -> UsersTab.tsx:109

## E2E Test Suite Rewrite (2026-02-05)

**Status: ✅ COMPLETED** - All E2E tests rewritten for route-based architecture

### Architecture Changes Applied
- Modal-based → Route-based navigation
- `/proxies/new` for create page (was `#addInstanceModal`)
- `/proxies/:name/settings` for settings page (was `#settingsModal`)
- Card-based layout (was tab-based with `data-tab` attributes)

### Files Rewritten
1. `tests/e2e/utils.py` - Added navigation helpers and API polling utilities
2. `tests/e2e/test_scenarios.py` - 16 tests rewritten (841 lines)
3. `tests/e2e/test_edge_cases.py` - 9 tests rewritten (330 lines)
4. `tests/e2e/test_https_features.py` - 8 tests rewritten (369 lines)

### New Helper Functions Added
- `create_instance_via_ui()` - Full create flow with navigation
- `navigate_to_settings()` - Navigate to settings page
- `navigate_to_dashboard()` - Return to dashboard
- `wait_for_instance_running()` - API polling for running state
- `wait_for_instance_stopped()` - API polling for stopped state
- `get_icon_color()` - Extract ha-icon color from inline styles
- `is_success_color()` / `is_error_color()` - Color validation

### Key Pattern Changes
- **Status checks**: API polling (no `data-status` attribute)
- **Icon colors**: Check `ha-icon` inline styles (not SVG classes)
- **User chips**: `user-chip-{username}` (was `user-item[data-username]`)
- **Settings navigation**: Must manually navigate back to dashboard after save

### Syntax Verified
All files pass `python3 -m py_compile` with no errors.

## UI Redesign v1.5.2+ (2026-02-06)

### Instance Card Visual Redesign
**Status indication changed from text to visual elements:**
- **Running**: Green background tint `rgba(67,160,71,0.15)`, green icon, green status dot overlay
- **Stopped**: Gray background tint `rgba(158,158,158,0.15)`, gray icon, NO status dot
- Card no longer shows "Running"/"Stopped" text labels
- Tests must check visual indicators (buttons, status dots) NOT text

### Logs Section Moved to Dialog
**Breaking change in settings page:**
- Previously: Logs displayed inline on settings page
- Now: Logs in modal dialog opened via button
- Access pattern: Click `[data-testid="settings-view-logs-button"]` → dialog with `[data-testid="logs-type-select"]`
- "Instance Logs" h2 removed - now a card with action button

### Icon Color Detection Update
`get_icon_color()` utility updated to detect status dot background color (new UI pattern):
- Status dot = small colored circle overlay on icon wrapper
- Green dot = running, no dot = stopped
- Old approach (ha-icon color) no longer applicable

## Critical Backend Findings (2026-02-10)

### Container Crash on Certificate Regeneration (INTERMITTENT)
- Addon container exits with code 137 after cert regen under load
- Sequence: cert regen -> stop squid (SIGTERM->SIGKILL) -> start new squid -> s6-rc stops
- NOT reliably reproducible - works in isolation, crashes under full suite load
- **Workaround**: `wait_for_addon_healthy()` + connection error recovery in tests
- **File**: `squid_proxy_manager/rootfs/etc/services.d/squid-proxy-manager/finish`

### User Add API 500 During Proxy Restart
- Each user add triggers proxy stop/start cycle (~5-8s)
- API returns 500 during restart window
- **Fix**: Wait for `wait_for_instance_running()` before each add, retry on 500

### User Chip Rendering Delay (~9s via UI)
- react-query mutation -> proxy restart -> query invalidation -> refetch -> chip render
- **Decision**: Use API calls for user management in tests (not UI form)
- For chip verification: navigate fresh to force data reload

### Process Group Isolation Verified
- `os.setsid` in `Popen.preexec_fn` correctly isolates child process groups
- Python and Squid have separate PGID/SID values
- `os.killpg` targets only child's group, not parent

### Cleanup Fixture Enhancement
- `auto_cleanup_instances_after_test` now waits for addon health before cleanup
- Prevents cascading failures when addon crashed during previous test
