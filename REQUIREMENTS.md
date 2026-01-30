# Squid Proxy Manager - Requirements

**Cross-Reference**: [TEST_PLAN.md](TEST_PLAN.md) - 7 User Scenarios with comprehensive testing coverage

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

### v1.1.14: User Auth Isolation
**Issue**: Users shared between instances (407 auth error)
**Root Cause**: Single passwd file for all instances
**Fix**: Each instance gets isolated passwd at `/data/squid_proxy_manager/{name}/passwd`
**Test**: `tests/unit/test_auth_manager.py`

### v1.1.16: Certificate Permissions
**Issue**: HTTPS enable fails (`FATAL: No valid signing certificate`)
**Root Cause**: Cert file perms 0o755 (dir mode); Squid can't read
**Fix**: Changed to 0o644 (file mode)
**Test**: `tests/integration/test_file_permissions.py`

### v1.1.17: Certificate Type (CA vs Server)
**Issue**: HTTPS still fails even with correct perms
**Root Cause**: Cert generated as CA (`BasicConstraints(ca=True)`); Squid's `https_port` needs server cert
**Fix**: Set `BasicConstraints(ca=False)`, added `ExtendedKeyUsage(SERVER_AUTH)`, removed `ssl_bump` directive
**Test**: `tests/unit/test_squid_config_https.py`, `test_cert_manager.py`

### v1.1.18: Key File Permissions + UI
**Issue**: Key file 0o600 still prevents Squid reading; modal styling broken
**Root Cause**: Squid user needs read access to key; ingress iframe blocks `window.confirm()`
**Fix**: Changed key to 0o644; custom HTML modal dialogs
**Test**: E2E UI tests, `test_full_flow.py`

### v1.2.1: Security Hardening
**Focus**: Container and data security
**Changes**: Non-root (UID 1000:1000), dropped capabilities, read-only fs, security scanning
**Test**: Integration checks, CI Trivy scan

### v1.3.0–1.3.8: React SPA
**Focus**: UI modernization + Docker-first workflow
**Changes**: React + Vite + Tailwind, Figma components, Docker frontend tests (Vitest), E2E with Playwright
**Test**: Frontend unit tests, E2E flows

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
