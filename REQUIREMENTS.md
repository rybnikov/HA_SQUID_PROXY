# Squid Proxy Manager - Requirements

**Cross-Reference**: [TEST_PLAN.md](TEST_PLAN.md) - 9 User Scenarios with comprehensive testing coverage

## Project Overview

Home Assistant Add-on that manages multiple Squid proxy instances with HTTPS support and basic authentication. Built as a React SPA with Docker-first development, security hardening, and comprehensive testing.

## Functional Requirements

### FR-1: Proxy Instance Management
- Create new instances (name, port, HTTPS option)
- Start/Stop/Restart instances
- Delete instances (clean config, logs, certs)
- List all instances with status
- Update settings (port, HTTPS toggle)

### FR-2: User Authentication
- Add/remove users per instance
- Instance-isolated passwd files
- Multiple users per instance
- MD5-crypt (APR1) password hashing for Squid

### FR-3: HTTPS Support
- Enable HTTPS on instances
- Generate self-signed server certificates (server type, not CA)
- Customizable cert parameters (CN, validity, key size, org)
- Regenerate certs on demand
- File permissions: cert+key 0o644 (readable by proxy user)

### FR-4: Web UI (React SPA)
Dashboard and modal-driven interface for managing all instance settings.

**FR-4.1: Dashboard**
- Show all instances as cards (name, port, status, enabled/disabled toggle)
- Quick-action buttons: Start/Stop, Delete, Settings, View Logs
- Add Instance button
- Search/filter instances by name

**FR-4.2: Add Instance Modal**
- Tab 1 "Basic": Name, Port (3128-3140), HTTPS toggle
- Tab 2 "HTTPS Settings" (visible only if HTTPS enabled):
  - Certificate Common Name (CN)
  - Organization
  - Country Code
  - Validity days (365 default)
  - Key size (2048/4096)
  - Action: Generate Certificate
- Tab 3 "Users": Add initial users (username/password pairs)
- Tab 4 "Test": Connectivity check after creation (HTTP GET, display response status)
- Submit button: Create Instance (all tabs validated)

**FR-4.3: Instance Settings Modal**
- Tab 1 "General": Instance name (read-only), Port (editable), HTTPS toggle (with enable/disable)
- Tab 2 "HTTPS": Show current cert info (CN, validity, expires), Regenerate button
- Tab 3 "Users": List users with Add/Remove buttons per user
- Tab 4 "Test": Connectivity (HTTP GET to proxy), display status, response time, headers
- Tab 5 "Logs": Dropdown selector (access.log or cache.log), viewer with scroll
- Submit/Save button: Update settings

**FR-4.4: User Management (inside Settings > Users Tab)**
- List all users for instance
- Add user form (username, password)
- Delete button per user (with custom confirm modal, not window.confirm)
- Async indicators during add/remove

**FR-4.5: Log Viewer (inside Settings > Logs Tab)**
- Dropdown: Select log file (access.log, cache.log)
- Display log content (last 500 lines)
- Auto-refresh toggle (every 5 seconds)
- Download button
- Search box (client-side filter)

**FR-4.6: Test Connectivity (inside modals)**
- Button: Test Proxy
- Shows: HTTP status, response time, headers
- Display success/error in modal
- Async spinner during request

**FR-4.7: Progress Indicators**
- Add user: Spinner + "Creating user..." text
- Delete instance: Spinner + "Deleting..."
- Buttons disabled during async ops
- Errors shown in red toast or inline

**FR-4.8: Routing & Deep-Links**
- All navigation via React Router (not page reloads)
- Routes: /, /instances, /instances/{id}/settings, /logs/{id}
- Deep-link safe: Refresh on /instances/my-proxy/settings works (server fallback to index.html)
- Ingress-safe: Handles HA proxy path rewriting (runtime basename detection)

**FR-4.9: Modal Dialogs**
- Custom HTML modals (not window.confirm, window.alert)
- Delete confirm modal: "Delete 'proxy-name'?" with Cancel/Delete buttons
- Error modal: Displays error message with Close button
- Success toast: "Instance created successfully" (auto-hide 3s)

### FR-5: API Endpoints
- GET /api/instances
- POST /api/instances
- DELETE /api/instances/{name}
- POST /api/instances/{name}/start
- POST /api/instances/{name}/stop
- PATCH /api/instances/{name}
- POST /api/instances/{name}/users
- DELETE /api/instances/{name}/users/{username}
- POST /api/instances/{name}/certs
- POST /api/instances/{name}/test
- POST /api/instances/{name}/patch-openvpn (Squid and TLS Tunnel)

### FR-6: OpenVPN Config Patcher

**Goal**: Provide a dialog-based tool to automatically patch OpenVPN config files with proxy directives and authentication credentials, without manual editing or syntax errors.

**Key Requirements**:
- Dialog accessible from instance settings (not a dedicated tab)
- Context-aware behavior for Squid vs TLS Tunnel instances
- Progressive disclosure (show only relevant options)
- No `window.alert()` or `window.confirm()` calls (HA ingress compatible)
- Inline feedback for errors and success states
- All HA-native components (HADialog, HAButton, HACard, HASwitch, HATextField, HASelect)

**FR-6.1: Dialog Accessibility**
- Squid instances: Accessible from Test Connectivity tab ("Patch OpenVPN Config" button)
- TLS Tunnel instances: Accessible from Connection Info tab ("Patch OpenVPN Config" button)
- Dialog opens as modal overlay (doesn't navigate away from settings)
- Keyboard navigation: Escape key closes dialog
- Click outside dialog (backdrop) closes dialog
- Close button in dialog footer

**FR-6.2: File Upload**
- Hidden file input + styled HAButton trigger
- Accept only `.ovpn` files
- Show filename and size after selection
- Inline error message for invalid file types
- Replace file button if already uploaded

**FR-6.3: Progressive Disclosure - Squid Instances**
- Info card: "Upload your .ovpn file to add HTTP proxy directives"
- File upload section (always visible)
- Authentication section (optional, toggled with HASwitch):
  - User dropdown (if users exist for instance)
  - Manual username field
  - Manual password field (type="password")
- External IP warning card (if not configured): "External IP not set. Config will use 'localhost'. Action: Set external IP in General settings."
- Primary action button: "Patch Config"

**FR-6.4: Progressive Disclosure - TLS Tunnel Instances**
- Info card: "Upload your .ovpn file to extract VPN server and configure TLS tunnel"
- File upload section (always visible)
- NO authentication section (hidden entirely, not disabled)
- External IP warning card (if not configured)
- Primary action button: "Extract & Patch"

**FR-6.5: Patching Logic - Squid**
- Parse uploaded .ovpn file
- Extract remote server and port
- Add `http-proxy <external_ip or localhost>:<proxy_port>` directive
- If auth enabled: Add `http-proxy-userpass <username> <password>` inline (not separate file)
- Return patched config as string

**FR-6.6: Patching Logic - TLS Tunnel**
- Parse uploaded .ovpn file
- Extract `remote <server> <port>` directive
- Configure TLS tunnel to route to extracted server:port
- Return patched config with tunnel directives

**FR-6.7: Preview and Download**
- Preview section (appears after successful patch):
  - Read-only textarea with patched config (300px height, monospace font)
  - Scrollable if content exceeds height
  - Styled with HA CSS variables (--secondary-background-color, --primary-text-color)
- Download button: Downloads patched config as `.ovpn` file
- Copy button: Copies patched config to clipboard
- Copy success feedback: "✓ Copied to clipboard" (auto-hide after 3s, optimistic UI)

**FR-6.8: Inline Feedback (No Alerts)**
- File error: Inline error message in red (var(--error-color))
- Upload success: Show filename + size in secondary text
- Patch error: Inline error message below primary button
- Patch success: Preview section appears
- Copy success: Inline success message (auto-hide 3s)
- External IP warning: Amber warning card with border-left accent

**FR-6.9: Loading States**
- Primary button (Patch Config / Extract & Patch):
  - Show loading spinner during API call
  - Disable button during loading
  - Component-level loading (not full dialog)
- Copy button: Immediate optimistic feedback (no loading)

**FR-6.10: Component Standards**
- All components use HA wrappers (HADialog, HAButton, HACard, HAIcon, HASwitch, HATextField, HASelect)
- Layout uses inline styles (not Tailwind classes)
- Colors use HA CSS variables (--primary-text-color, --error-color, --success-color, --warning-color, --divider-color)
- Spacing scale: 16px section gaps, 12px field gaps, 8px inline gaps
- All interactive elements have data-testid attributes

**FR-6.11: Acceptance Criteria**
- ✅ Dialog opens from correct tab (Test Connectivity for Squid, Connection Info for TLS)
- ✅ Progressive disclosure: Auth section visible only for Squid
- ✅ File upload validates .ovpn extension
- ✅ Patched config includes correct directives (http-proxy for Squid, tunnel config for TLS)
- ✅ Download and copy functionality work
- ✅ Copy success message auto-hides after 3 seconds
- ✅ No window.alert() or window.confirm() calls (HA ingress compatible)
- ✅ External IP warning shows when not configured
- ✅ All data-testid attributes present for E2E testing
- ✅ Dialog closes on Escape key, backdrop click, or close button
- ✅ Loading states on primary button (not full dialog)

**Critical Bug Fixed**: Original OpenVPNTab implementation used `window.alert()` (3 instances) which is BLOCKED in Home Assistant ingress iframes. Refactored to use inline feedback states, ensuring feature works in production HA environment.

## User Scenarios

### Scenario 1: Setup First Proxy with Authentication
**Actor**: Home Assistant admin user
**Goal**: Create a working proxy with basic auth
**Steps**:
1. Open Squid Proxy Manager UI
2. Click "Add Instance"
3. Enter name "office-proxy", port 3128, disable HTTPS
4. Go to Users tab, add user "alice" / "password123"
5. Go to Test tab, click "Test Proxy" → sees HTTP 407 (auth required)
6. Add user "bob", confirm both users added
7. Click Create → instance starts, modal closes
8. Dashboard shows "office-proxy" running

**Expected Outcome**: Instance running on port 3128, accepts requests from alice/bob, rejects unauthenticated requests (407)
**Test Coverage**: [TEST_PLAN.md - Scenario 1](TEST_PLAN.md#scenario-1-setup-first-proxy-with-authentication) with 8-step test table, automated + manual checks

### Scenario 2: Enable HTTPS on Existing Instance
**Actor**: Admin
**Goal**: Enable HTTPS on running proxy
**Steps**:
1. Click instance → Settings modal opens
2. Go to General tab, toggle HTTPS ON
3. Modal switches to HTTPS tab (now visible)
4. Enter cert CN="proxy.home.local", Org="Home"
5. Click "Generate Certificate" → spinner, then "Certificate generated"
6. Go to Test tab, click "Test Proxy" → status shows HTTPS port active
7. Click Save → instance restarts with HTTPS

**Expected Outcome**: Instance now listens on HTTPS port, cert generated with correct CN, test confirms connectivity
**Test Coverage**: [TEST_PLAN.md - Scenario 2](TEST_PLAN.md#scenario-2-enable-https-on-existing-instance) with 8-step test table, cert verification + HTTPS functionality

### Scenario 3: Troubleshoot Authentication Failure
**Actor**: User reporting "407 Proxy Auth Required"
**Goal**: Verify user credentials
**Steps**:
1. Open Squid Proxy Manager
2. Click instance → Settings
3. Go to Users tab → see list of users (alice, bob)
4. Realize user "charlie" is missing
5. Click Add User, enter charlie/secret
6. Go to Test tab → click "Test Proxy" as charlie → HTTP 200 (success)
7. Advise user to update proxy credentials

**Expected Outcome**: User charlie added to instance, can now authenticate
**Test Coverage**: [TEST_PLAN.md - Scenario 3](TEST_PLAN.md#scenario-3-troubleshoot-authentication-failure) with 5-step test table, user management flow

### Scenario 4: Monitor Proxy Traffic
**Actor**: Admin
**Goal**: Check what's being proxied
**Steps**:
1. Open Squid Proxy Manager → select instance
2. Click Settings → Logs tab
3. Dropdown: Select "access.log"
4. See last 500 lines of client requests (IP, time, URL, status, bytes)
5. Toggle "Auto-refresh" → log updates every 5 sec
6. Search box: filter by client IP "192.168.1.10"
7. Click Download → get full access.log file

**Expected Outcome**: Admin can see proxy traffic, filter, and export logs
**Test Coverage**: [TEST_PLAN.md - Scenario 4](TEST_PLAN.md#scenario-4-monitor-proxy-traffic) with 6-step test table, log viewer + auto-refresh + search

### Scenario 5: Manage Multiple Proxies
**Actor**: Admin
**Goal**: Run separate proxies for office, remote, and internal use
**Steps**:
1. Dashboard shows 0 instances
2. Create "office" (3128, no HTTPS, users: alice, bob)
3. Create "remote" (3129, HTTPS, users: charlie, dave)
4. Create "internal" (3130, no HTTPS, no users, open to local network)
5. Dashboard now shows 3 instances as cards
6. Toggle "remote" OFF (stop without deleting)
7. Click "office" → edit port to 3128, save
8. Delete "internal" → confirm modal → instance removed

**Expected Outcome**: Multiple instances running independently, each with own config/users/logs
**Test Coverage**: [TEST_PLAN.md - Scenario 5](TEST_PLAN.md#scenario-5-manage-multiple-proxies) with 10-step test table, multi-instance isolation + lifecycle

### Scenario 6: Certificate Expired, Regenerate
**Actor**: Admin noticing browser SSL warnings
**Goal**: Regenerate cert with longer validity
**Steps**:
1. Open instance Settings
2. HTTPS tab shows cert expires in 30 days
3. Click "Regenerate Certificate"
4. Modal appears: adjust validity to 730 days
5. Click "Generate" → spinner, cert regenerated
6. Test tab shows HTTPS still working
7. Browser no longer warns about expiry

**Expected Outcome**: New cert generated, instance restarts, HTTPS connection validated
**Test Coverage**: [TEST_PLAN.md - Scenario 6](TEST_PLAN.md#scenario-6-certificate-expired-regenerate) with 7-step test table, cert validity + regeneration

### Scenario 7: Start/Stop Without Deleting
**Actor**: Admin
**Goal**: Temporarily disable proxy for maintenance
**Steps**:
1. Dashboard shows "office-proxy" running
2. Click "Stop" button on card
3. Instance status changes to "Stopped"
4. Later, click "Start" → instance resumes (same config/users preserved)
5. Settings still intact, no data loss

**Expected Outcome**: Instance can be stopped/started without losing configuration
**Test Coverage**: [TEST_PLAN.md - Scenario 7](TEST_PLAN.md#scenario-7-startstop-without-deleting) with 8-step test table, process lifecycle + state preservation

### Scenario 8: Patch OpenVPN Config for Squid Proxy
**Actor**: User setting up VPN with proxy routing
**Goal**: Automatically patch OpenVPN config to route through Squid proxy with authentication
**Steps**:
1. Navigate to running Squid instance "office-proxy" settings
2. Go to Test Connectivity tab
3. Click "Patch OpenVPN Config" button → dialog opens
4. See info card: "Upload your .ovpn file to add HTTP proxy directives"
5. Click "Select .ovpn File" button → file picker opens
6. Select `my-vpn.ovpn` file → see filename and size below button
7. Toggle "Include authentication" switch ON
8. See user dropdown with existing users (alice, bob)
9. Select "alice" from dropdown → username field auto-fills
10. Click "Patch Config" button → see loading spinner
11. Preview section appears with patched config showing:
    - `http-proxy 192.168.1.100 3128`
    - `http-proxy-userpass alice password123`
12. Click "Download" → file downloads as `my-vpn-patched.ovpn`
13. Click "Copy" → see success message "✓ Copied to clipboard"
14. Success message auto-hides after 3 seconds
15. Close dialog → return to settings without losing context

**Expected Outcome**:
- Dialog accessible from Test Connectivity tab (not separate page)
- File upload validates .ovpn extension
- Auth section visible and functional for Squid instances
- Patched config includes correct proxy directives and credentials
- Download and copy work correctly
- No `window.alert()` or browser dialogs (HA ingress compatible)
- Context preserved (still in settings after closing dialog)

**Test Coverage**: [TEST_PLAN.md - OpenVPN Dialog](TEST_PLAN.md#openvpn-config-patcher-dialog) with 22-step test table covering dialog accessibility, file upload, progressive disclosure, patching, preview, download, copy, and keyboard navigation

### Scenario 9: Patch OpenVPN Config for TLS Tunnel
**Actor**: User setting up VPN with TLS tunnel
**Goal**: Extract VPN server from OpenVPN config and configure TLS tunnel routing
**Steps**:
1. Navigate to running TLS Tunnel instance "tunnel-443" settings
2. Go to Connection Info tab
3. Click "Patch OpenVPN Config" button → dialog opens
4. See info card: "Upload your .ovpn file to extract VPN server and configure TLS tunnel"
5. Notice NO authentication section (progressive disclosure)
6. Click "Select .ovpn File" → choose `vpn-server.ovpn`
7. Click "Extract & Patch" button → loading state
8. Preview shows extracted server `remote vpn.example.com 1194` and tunnel config
9. Click "Copy" → success message appears
10. Close dialog → return to Connection Info tab

**Expected Outcome**:
- Dialog accessible from Connection Info tab (different from Squid)
- NO authentication section visible (TLS tunnels don't use auth)
- Server extraction works correctly
- Different button text: "Extract & Patch" vs "Patch Config"
- Progressive disclosure prevents confusion (no disabled auth fields)

**Test Coverage**: [TEST_PLAN.md - OpenVPN Dialog](TEST_PLAN.md#openvpn-config-patcher-dialog) - TLS-specific tests for conditional rendering and server extraction

## Non-Functional Requirements

### NFR-1: Security
- Passwords: MD5-crypt hashes (no plaintext)
- Container: Non-root (UID 1000:1000)
- Capabilities: `CAP_DROP all` except NET_BIND_SERVICE
- Filesystem: Read-only root with tmpfs /tmp, /run
- Secrets: No secrets in logs
- CVE scan: Trivy/Anchore blocks HIGH/CRITICAL

### NFR-2: Performance
- Async cert generation
- Non-blocking UI for long ops
- TanStack Query for efficient server state

### NFR-3: Reliability
- Certificate validation before Squid start
- Graceful error handling
- Process cleanup on delete
- Squid 5.9 with real binary in tests

### NFR-4: Compatibility
- Home Assistant Add-on format
- Ingress support (runtime basename)
- Deep-link refresh safe
- Alpine Linux 3.20+

## Known Issues & Fixes (Regression Prevention)

### v1.4.8: E2E Cleanup in Parallel Runs
**Issue**: E2E suite intermittently failed in parallel runs due to stale instances not being cleaned up.
**Root Cause**: Cleanup fixture matched worker IDs like `gw0`, but instance names use `w0` pattern, so cleanup never ran.
**Fix**: Normalize worker ID to `w{n}-` and delete only matching instances after each test.
**Test**: `tests/e2e/test_scenarios.py::test_scenario_6_regenerate_cert`, `tests/e2e/test_scenarios.py::test_https_critical_no_ssl_bump`

### v1.4.0: Unified Recording Pipeline
**Focus**: Simplified workflow recording and development tooling
**Changes**: Consolidated `record_workflows.sh` into single unified script with addon lifecycle management
**Features**:
- Single command: `./pre_release_scripts/record_workflows.sh` (no parameters)
- Manages addon startup, health checks, Docker recording, cleanup
- Automatic GIF generation for README workflows
- Color-coded progress output
**Test**: Manual testing with addon and Docker container validation

### v1.3.0–1.3.8: React SPA
**Focus**: UI modernization + Docker-first workflow
**Changes**: React + Vite + Tailwind, Figma components, Docker frontend tests (Vitest), E2E with Playwright
**Test**: Frontend unit tests, E2E flows

### v1.2.1: Security Hardening
**Focus**: Container and data security
**Changes**: Non-root (UID 1000:1000), dropped capabilities, read-only fs, security scanning
**Test**: Integration checks, CI Trivy scan

### v1.1.18: Key File Permissions + UI
**Issue**: Key file 0o600 still prevents Squid reading; modal styling broken
**Root Cause**: Squid user needs read access to key; ingress iframe blocks `window.confirm()`
**Fix**: Changed key to 0o644; custom HTML modal dialogs
**Test**: E2E UI tests, `test_full_flow.py`

### v1.1.17: Certificate Type (CA vs Server)
**Issue**: HTTPS still fails even with correct perms
**Root Cause**: Cert generated as CA (`BasicConstraints(ca=True)`); Squid's `https_port` needs server cert
**Fix**: Set `BasicConstraints(ca=False)`, added `ExtendedKeyUsage(SERVER_AUTH)`, removed `ssl_bump` directive
**Test**: `tests/unit/test_squid_config_https.py`, `test_cert_manager.py`

### v1.1.16: Certificate Permissions
**Issue**: HTTPS enable fails (`FATAL: No valid signing certificate`)
**Root Cause**: Cert file perms 0o755 (dir mode); Squid can't read
**Fix**: Changed to 0o644 (file mode)
**Test**: `tests/integration/test_file_permissions.py`

### v1.1.14: User Auth Isolation
**Issue**: Users shared between instances (407 auth error)
**Root Cause**: Single passwd file for all instances
**Fix**: Each instance gets isolated passwd at `/data/squid_proxy_manager/{name}/passwd`
**Test**: `tests/unit/test_auth_manager.py`

## Architecture Decisions

### AD-1: Process-based Squid Management
Each instance = separate Squid process via `subprocess.Popen` with `-N` (no daemon).
**Why**: Isolation, independent lifecycle control, straightforward cleanup.

### AD-2: Per-Instance Auth Files
Each instance has isolated passwd at `/data/squid_proxy_manager/{name}/passwd`.
**Why**: Security & isolation — shared passwd file breaks multi-user authentication.

### AD-3: Certificate Permissions (0o644)
Both cert and key readable by Squid (UID 101).
**Why**: Squid proxy user must read keys; 0o600 causes `FATAL: No valid signing certificate`.

### AD-4: HTTPS Without ssl_bump
`https_port [::]:PORT tls-cert=... tls-key=...` with NO `ssl_bump` directive.
**Why**: `ssl_bump` requires CA cert even with `none all`; unnecessary for simple encrypted proxy connection.

### AD-5: React SPA Frontend
Frontend is React + Vite + Tailwind SPA with feature-based architecture, not embedded HTML string.
**Why**: Better UX, state management (TanStack Query), testing (Vitest), maintainability.

### AD-6: Container Security
Non-root (UID 1000:1000), dropped capabilities, read-only root filesystem.
**Why**: Reduce attack surface — standard container hardening practice.

## Release Checklist

1. All CI gates pass:
   - Lint: `pre-commit run --all-files` (0 issues)
   - Security: `bandit`, Trivy/Anchore (0 HIGH/CRITICAL)
   - Unit + Integration: `./run_tests.sh unit` (all pass)
   - E2E: `./run_tests.sh e2e` (all flows pass)

2. Version bumped:
   - `config.yaml`: `version: "X.Y.Z"`
   - `Dockerfile`: `io.hass.version="X.Y.Z"`
   - `main.py`: version string(s) if present

3. Docs updated:
   - REQUIREMENTS.md: version entry + known issues
   - TEST_PLAN.md: test notes
   - Commit: `release: vX.Y.Z - [summary]`

4. Tag and push:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin main --tags
   ```

## Documentation Maintenance Rules

**When fixing a bug or adding a feature:**

1. **Update REQUIREMENTS.md**:
   - Add entry under "Known Issues & Fixes" (copy template)
   - Include: Issue, Root Cause, Fix, Test reference

2. **Update TEST_PLAN.md**:
   - Add/update row in "Test Coverage by Feature"
   - Mark status: ✅ (passing) or [ ] (pending)

3. **Update DEVELOPMENT.md**:
   - Add troubleshooting if new issue
   - Update Common Issues table

4. **Commit message**:
   ```
   fix: [brief issue]

   - Issue: [user-visible problem]
   - Root cause: [why]
   - Fix: [code/config change]
   - Tests: [test file/function references]
   - Docs: REQUIREMENTS.md, TEST_PLAN.md
   ```

## Test Counts & Status

| Suite | Count | Status |
|-------|-------|--------|
| Unit | 40+ | ✅ Pass |
| Integration | 20+ | ✅ Pass |
| Frontend Unit | 10+ | ✅ Pass |
| E2E | 10+ | ✅ Pass |
| Security | — | ✅ Pass |
| Lint | — | ✅ Pass |

All tests run in Docker with real Squid binary.

---

## Document Alignment

### REQUIREMENTS.md ↔ TEST_PLAN.md Mapping

**User Scenarios** (7 total):
- Each scenario in REQUIREMENTS.md (FR/NFR context) has corresponding test section in TEST_PLAN.md
- TEST_PLAN provides: acceptance criteria → test procedures → automated tests + manual checks
- REQUIREMENTS provides: acceptance criteria + expected outcomes

**Functional Requirements** (FR-1 to FR-5):
- FR-1 (Instance Mgmt): Core Functionality Tests + Scenarios 1, 5, 7
- FR-2 (Auth): Authentication Tests + Scenarios 1, 3, 5
- FR-3 (HTTPS): HTTPS Tests + Scenarios 2, 6
- FR-4 (Web UI): React SPA Frontend Tests + all scenarios
- FR-5 (API): Feature-Level Test Coverage tables

**Non-Functional Requirements** (NFR-1 to NFR-4):
- NFR-1 (Security): Security Tests section
- NFR-2 (Performance): E2E async tests, log auto-refresh
- NFR-3 (Reliability): Integration tests, error scenarios
- NFR-4 (Compatibility): E2E ingress routing, deep-link safety

**Edge Cases & Negative Scenarios**:
- REQUIREMENTS.md lists "Known Issues & Fixes" (root causes, regression prevention)
- TEST_PLAN.md lists comprehensive edge cases, boundary conditions, race conditions, error recovery
- Both ensure no regression when adding features

---

## How to Use These Documents

### For Feature Development:
1. Read REQUIREMENTS.md: FR defines what to build
2. Read TEST_PLAN.md: Section headings show how to test it
3. Implement feature + tests together
4. Run: `./run_tests.sh`

### For Bug Investigation:
1. Check REQUIREMENTS.md "Known Issues & Fixes" for root cause context
2. Find matching test in TEST_PLAN.md
3. Verify test reproduces issue
4. Fix code, verify test passes

### For Release:
1. REQUIREMENTS.md: Check version, CI gates, docs updated
2. TEST_PLAN.md: Run all suites (unit, integration, E2E)
3. DEVELOPMENT.md: Follow release checklist, tag, push

### For QA/Testing:
1. TEST_PLAN.md: Use "Manual Testing Checklist" (30 min pre-release)
2. Run automated suites: `./run_tests.sh`
3. Check edge cases section if time permits

## HA-Native UI Requirement (Ingress)

### Requirement

Ingress-facing UI primitives must use Home Assistant native web components through project wrappers.

### Scope

Applies to instance management pages:

- `DashboardPage`
- `ProxyCreatePage`
- `ProxyDetailsPage`
- `SettingsPage`

### Rationale

- Visual and behavioral consistency with Home Assistant
- Better theme compatibility in ingress context
- Clear separation between business logic (React) and primitives (HA wrappers)
