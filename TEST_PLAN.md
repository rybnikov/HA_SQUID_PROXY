# Squid Proxy Manager - Test Plan

**Cross-Reference**: [REQUIREMENTS.md](REQUIREMENTS.md) - Functional Requirements (FR-1 to FR-5), Non-Functional Requirements (NFR-1 to NFR-4), User Scenarios (1-7)

## Overview

Test plan covers all user scenarios from REQUIREMENTS.md, mapped to automated tests and manual verification procedures. Tests run in Docker with real Squid binary for accuracy.

**v1.4.5 Changes**: Settings modal tabs redesigned for responsive layout:
- **Mobile (<768px)**: Horizontal scrollable tabs at top
- **Tablet/Desktop (≥768px)**: Vertical tabs on left, content on right
- **Scrollable content**: Prevents modal overflow and horizontal jumps
- **Backward Compatible**: All E2E tests work without modification (data-tab attributes preserved)

### Scenario Coverage Matrix

| Scenario | REQUIREMENTS | TEST_PLAN | Focus Area |
|----------|---|---|---|
| 1. Setup First Proxy with Authentication | Scenario 1 | Section 1 | FR-1, FR-2, Create+Add Users |
| 2. Enable HTTPS on Existing Instance | Scenario 2 | Section 2 | FR-3, Cert Generation |
| 3. Troubleshoot Authentication Failure | Scenario 3 | Section 3 | FR-2, User Management |
| 4. Monitor Proxy Traffic | Scenario 4 | Section 4 | FR-4.5, Log Viewer |
| 5. Manage Multiple Proxies | Scenario 5 | Section 5 | FR-1, Multi-instance |
| 6. Certificate Expired, Regenerate | Scenario 6 | Section 6 | FR-3, Cert Regeneration |
| 7. Start/Stop Without Deleting | Scenario 7 | Section 7 | FR-1, Process Lifecycle |

## Running Tests

### Full Test Suite

```bash
# All tests in Docker (unit + integration + e2e)
./run_tests.sh

# Fast suite (unit + integration only) - ~60 seconds
./run_tests.sh unit

# E2E only (real addon + Playwright browser) - ~180 seconds
./run_tests.sh e2e

# Parallel execution with xdist
pytest tests/ -n auto                  # Auto-detect worker count
pytest tests/e2e/ -n 4                 # 4 parallel workers
pytest tests/unit/ -n auto -v          # Unit tests parallel

# Single test or debug mode
pytest tests/unit/test_auth_manager.py::test_add_user -v
pytest tests/e2e/test_scenarios.py::test_scenario_1_setup_proxy_with_auth -n 1 -v
```

### E2E Test Best Practices

**⚠️ CRITICAL**: Follow these best practices to ensure reliable, maintainable E2E tests:

#### 1. Use data-testid Selectors (ALWAYS)

**✅ DO**: Use data-testid attributes for all interactive elements
```python
# Good: Stable, semantic selector
await page.click('[data-testid="instance-create-button"]')
await page.fill('[data-testid="instance-name-input"]', "proxy1")
await page.wait_for_selector('[data-testid="instance-card"][data-instance="proxy1"]')
```

**❌ DON'T**: Use CSS classes, text selectors, or brittle XPath
```python
# Bad: Breaks with UI changes
await page.click("button:has-text('Add Instance')")  # Text changes break test
await page.fill("#newName", "proxy1")                # ID changes break test
await page.click(".btn-primary")                     # Class changes break test
```

**React Component Pattern**:
```tsx
// Always add data-testid to interactive elements
<button data-testid="instance-create-button">Create Instance</button>
<input data-testid="instance-name-input" id="createName" {...register('name')} />
<div data-testid="instance-card" data-instance={instance.name} data-status={instance.running ? 'running' : 'stopped'}>
  <button data-testid="instance-start-button">Start</button>
  <button data-testid="instance-settings-button">Settings</button>
</div>
```

#### 2. Organize Tests for Maximum Parallelization

**✅ DO**: Keep tests independent and isolated
- Each test creates unique instances with `unique_name()` and `unique_port()`
- Tests clean up resources (instances deleted after test)
- No shared state between tests
- Use session-scoped fixtures for browser (one per worker)

**❌ DON'T**: Create dependencies between tests
- Don't rely on instances created in other tests
- Don't use global state or shared instance names
- Don't assume test execution order

**Parallel Execution Example**:
```bash
# Run E2E tests with 3 workers (optimal for most machines)
pytest tests/e2e/ -n 3 -v

# Auto-detect worker count
pytest tests/e2e/ -n auto -v
```

#### 3. Test Performance Optimization

**✅ DO**: Optimize waits and selectors
- Use `wait_for_selector()` with specific selectors (data-testid)
- Set reasonable timeouts (5-10s for UI, 30s for instance creation)
- Reuse browser sessions (session-scoped fixtures)
- Group related assertions in single test

**❌ DON'T**: Use arbitrary sleeps or slow selectors
- Don't use `asyncio.sleep()` except for intentional delays (e.g., testing instance stability)
- Don't use `wait_for_timeout()` without good reason
- Don't poll APIs unnecessarily (use wait_for_selector for UI updates)

#### 4. Running Failed Tests Only

When E2E tests fail, use pytest's built-in features to re-run only failures:

```bash
# First run: Some tests fail
./run_tests.sh e2e

# Re-run only failed tests (fast iteration)
pytest --lf tests/e2e/  # --lf = last failed

# Re-run failed + next tests
pytest --lf --ff tests/e2e/  # --ff = failed first

# Specific test for debugging
pytest tests/e2e/test_scenarios.py::test_scenario_1 -v -n 1 --tb=short
```

### E2E Test Artifacts (CI and Local)

When E2E tests run, Playwright automatically captures debugging artifacts on test failure:

**Artifact Types**:
- 📸 **Screenshots**: Captured at the exact point of failure
- 🎥 **Videos**: Full test execution recording (WebM format)
- 🔍 **Traces**: Detailed execution timeline with network activity, DOM snapshots, console logs

**Local Development**:
```bash
# Run E2E tests with artifact capture
./run_tests.sh e2e

# Artifacts automatically saved to: test-results/
# Structure:
# test-results/
#   └── <test-file>-<test-name>/
#       ├── test-failed-1.png      # Screenshot at failure
#       ├── video.webm             # Full test recording
#       └── trace.zip              # Detailed trace file

# View trace in Playwright Trace Viewer (best debugging tool)
playwright show-trace test-results/<test-name>/trace.zip
```

**CI Artifacts (GitHub Actions)**:
- ✅ **Automatically uploaded** when E2E tests fail
- ✅ **Retention**: 7 days (configurable in workflow)
- ✅ **Location**: GitHub Actions → Run → Artifacts section
- ✅ **Download**: "e2e-test-artifacts.zip"

**How to Access CI Artifacts**:
1. Go to failed GitHub Actions run page
2. Scroll to bottom → "Artifacts" section
3. Click "e2e-test-artifacts" to download
4. Extract ZIP and view traces:
   ```bash
   # Install Playwright locally (if needed)
   pip install playwright
   playwright install chromium

   # Open trace file
   playwright show-trace trace.zip
   ```

**What's in a Trace File?**:
- **Timeline**: Every action (click, fill, navigate) with timestamps
- **Network**: All HTTP requests/responses with status codes
- **Console**: JavaScript logs and errors from browser
- **DOM Snapshots**: Page state at each step (HTML/CSS)
- **Screenshots**: Visual state at each action
- **Performance**: Resource loading, rendering times

**Artifact Configuration** (see [pytest.ini](pytest.ini)):
- `--screenshot=only-on-failure`: Screenshot at failure point
- `--video=retain-on-failure`: Full test video recording
- `--tracing=retain-on-failure`: Detailed execution trace
- `--output=test-results/`: Output directory

**Example: Debugging a Failed Test**:
```bash
# 1. Test fails in CI
# 2. Download "e2e-test-artifacts.zip" from GitHub Actions
# 3. Extract and find trace file:
#    test-results/test-scenarios-test-scenario-1/trace.zip
# 4. Open in Trace Viewer:
playwright show-trace trace.zip
# 5. Investigate:
#    - Check timeline for unexpected actions
#    - Verify network requests succeeded
#    - Review console errors
#    - Compare DOM snapshots
```

**Trace Viewer UI**:
- **Actions Tab**: Click-by-click timeline
- **Metadata Tab**: Test info, browser, duration
- **Console Tab**: All console.log/error messages
- **Network Tab**: All HTTP calls with headers/body
- **Source Tab**: Test code execution path

For more details on artifact generation and configuration, see [DEVELOPMENT.md § E2E Test Artifacts & CI Reporting](DEVELOPMENT.md#e2e-test-artifacts--ci-reporting).

### Test Results

- **Unit Tests**: 40/40 passing ✅
- **Integration Tests**: 60/60 passing ✅
- **E2E Tests**: 37 tests (all passing)
- **Total**: 100+ tests passing
- **Execution Time**: ~14.5 seconds (parallel with xdist)
- **Success Rate**: 100%

### Test Coverage by Feature

| Feature | Tests | Status |
|---------|-------|--------|
| Authentication & Users | 10 | ✅ Passing |
| Certificate Management | 6 | ✅ Passing |
| Input Validation | 8 | ✅ Passing |
| Proxy Manager | 5 | ✅ Passing |
| Squid Config | 6 | ✅ Passing |
| HTTPS Configuration | 5 | ✅ Passing (NO ssl_bump) |
| API Endpoints | 20+ | ✅ Passing |
| Server Startup | 15+ | ✅ Passing |
| User Scenarios (7) | 7 | ✅ Passing |
| HTTPS Features | 10 | ✅ Passing |
| Edge Cases | 12+ | ✅ Passing |

---

## User Scenario Testing

### Scenario 1: Setup First Proxy with Authentication

**Goal**: Create a working proxy with basic auth
**Actors**: Home Assistant admin
**Acceptance Criteria**:
- Instance created with name, port, no HTTPS
- Two users added successfully
- Proxy running on specified port
- Unauthenticated requests return 407
- Authenticated requests (alice/bob) return 200

| Step | Test Procedure | Automated Test | Manual Check |
|------|---|---|---|
| Create instance | POST /api/instances with name="office-proxy", port=3128, https=false | `tests/unit/test_main.py::test_create_instance` | UI: Add Instance modal, fill "Basic" tab |
| Add user alice | POST /api/instances/office-proxy/users (alice/password123) | `tests/unit/test_auth_manager.py::test_add_user` | UI: Users tab shows "alice" |
| Add user bob | POST /api/instances/office-proxy/users (bob/password456) | — | UI: Users tab shows "alice", "bob" |
| Verify passwd isolated | Check `/data/squid_proxy_manager/office-proxy/passwd` exists and contains both users | `tests/unit/test_auth_manager.py::test_passwd_isolation` | Terminal: `grep alice /data/squid_proxy_manager/office-proxy/passwd` |
| Test unauthenticated | HTTP GET to proxy without auth headers | `tests/integration/test_e2e_flows.py::test_real_auth_fail` | `curl -x localhost:3128 http://example.com` → HTTP 407 |
| Test alice auth | HTTP GET with Proxy-Authorization (alice/password123) | `tests/integration/test_e2e_flows.py::test_real_auth_flow` | `curl -x localhost:3128 -U alice:password123 http://example.com` → HTTP 200 |
| Test bob auth | HTTP GET with Proxy-Authorization (bob/password456) | — | `curl -x localhost:3128 -U bob:password456 http://example.com` → HTTP 200 |
| Dashboard shows running | GET /api/instances returns instance with status="running" | `tests/integration/test_addon_structure.py::test_list_instances` | UI: Dashboard shows "office-proxy" card with "Running" badge |

---

### Scenario 2: Enable HTTPS on Existing Instance

**Goal**: Enable HTTPS on running proxy
**Actors**: Admin
**Acceptance Criteria**:
- HTTPS tab appears after toggling HTTPS ON
- Certificate generates with correct CN
- Instance restarts with HTTPS port active
- Test connectivity confirms HTTPS works
- Cert file permissions 0o644 (readable by Squid user)

| Step | Test Procedure | Automated Test | Manual Check |
|------|---|---|---|
| Toggle HTTPS ON | PATCH /api/instances/office-proxy with https=true | `tests/unit/test_main.py::test_update_instance` | UI: General tab, toggle HTTPS → HTTPS tab appears |
| Generate cert | POST /api/instances/office-proxy/certs (CN=proxy.home.local, Org=Home) | `tests/unit/test_cert_manager.py::test_generate_cert` | UI: HTTPS tab, fill cert params, click "Generate Certificate" |
| Verify cert type | Check cert has BasicConstraints(ca=False), ExtendedKeyUsage(SERVER_AUTH) | `tests/unit/test_cert_manager.py::test_cert_is_server_type` | Terminal: `openssl x509 -text -in /data/squid_proxy_manager/office-proxy/server.crt \| grep -A2 "Basic Constraints"` |
| Verify permissions | Check cert and key are 0o644 | `tests/integration/test_file_permissions.py::test_cert_key_readable` | Terminal: `ls -la /data/squid_proxy_manager/office-proxy/server.*` → rw-r--r-- |
| Squid config correct | Check config has "https_port ... tls-cert=... tls-key=..." with NO ssl_bump | `tests/unit/test_squid_config_https.py::test_https_config_no_ssl_bump` | Terminal: `grep https_port /data/squid_proxy_manager/office-proxy/squid.conf && ! grep ssl_bump` |
| Instance restarts | Process killed and respawned with new HTTPS config | `tests/integration/test_https_functional.py::test_https_proxy_works` | UI: Settings modal, click Save, wait for spinner to complete |
| Test HTTPS connectivity | HTTPS GET to proxy with valid cert (or --insecure) | `tests/e2e/test_https_ui.py::test_https_proxy_works` | `curl --proxy-insecure https://localhost:3128 -U alice:password123 https://example.com` → HTTP 200 |
| Instance shows HTTPS | GET /api/instances/office-proxy shows https=true | — | UI: Dashboard shows "HTTPS" badge on card |

---

### Scenario 3: Troubleshoot Authentication Failure

**Goal**: Verify user credentials and add missing user
**Actors**: Admin troubleshooting 407 errors
**Acceptance Criteria**:
- User list visible in Settings modal
- New user can be added and immediately authenticated
- Test connectivity confirms user works

| Step | Test Procedure | Automated Test | Manual Check |
|------|---|---|---|
| Open Settings | GET /api/instances/office-proxy | — | UI: Click instance card → Settings modal opens |
| View users tab | Modal shows all users (alice, bob) | — | UI: Users tab displays list with delete buttons |
| Add charlie user | POST /api/instances/office-proxy/users (charlie/secret) | `tests/unit/test_auth_manager.py::test_add_user` | UI: Click "Add User", fill form, submit → user appears in list |
| Verify passwd updated | Check charlie in `/data/squid_proxy_manager/office-proxy/passwd` | — | Terminal: `grep charlie /data/squid_proxy_manager/office-proxy/passwd` |
| Test charlie auth | HTTP GET with charlie credentials | — | `curl -x localhost:3128 -U charlie:secret http://example.com` → HTTP 200 |
| Test in UI | Click "Test Proxy" button in Settings | `tests/e2e/test_full_flow.py::test_connectivity` | UI: "Test Proxy" shows "✅ Connected (HTTP 200)" |

---

### Scenario 4: Monitor Proxy Traffic

**Goal**: Check what's being proxied via logs
**Actors**: Admin monitoring traffic
**Acceptance Criteria**:
- access.log displays recent client requests
- Logs show IP, timestamp, URL, status, bytes
- Auto-refresh updates every 5 seconds
- Search filter works client-side
- Download button exports full log

| Step | Test Procedure | Automated Test | Manual Check |
|------|---|---|---|
| Open Logs tab | GET /api/instances/office-proxy/logs | — | UI: Settings modal → Logs tab |
| Select access.log | Dropdown: access.log vs cache.log | `tests/unit/test_main.py::test_get_logs` | UI: Dropdown shows "access.log" (selected) and "cache.log" |
| Display log content | Read last 500 lines from access.log | `tests/integration/test_e2e_flows.py::test_real_auth_flow` (generates log entry) | UI: Logs viewer shows requests: "192.168.1.10 [timestamp] CONNECT example.com:443 200 1024" |
| Auto-refresh toggle | Enable auto-refresh, verify updates every 5s | `tests/e2e/test_full_flow.py::test_logs_auto_refresh` | UI: Toggle "Auto-refresh ON", make new proxy request, see new entry within 5s |
| Search box | Filter by client IP "192.168.1.10" | `tests/unit/test_main.py::test_search_logs` (frontend) | UI: Type "192.168.1" in search → logs filtered to matching entries |
| Download button | Click Download → file downloads | `tests/integration/test_main.py::test_download_logs` | Browser: Download access.log file, verify content matches UI |

---

### Scenario 5: Manage Multiple Proxies

**Goal**: Run separate proxies for office, remote, internal use
**Actors**: Admin managing multiple instances
**Acceptance Criteria**:
- Multiple instances created and listed
- Each instance has independent config/users/logs
- Stop/Start toggles instance without losing config
- Delete removes instance completely
- Dashboard shows all instances

| Step | Test Procedure | Automated Test | Manual Check |
|------|---|---|---|
| Create office instance | POST /api/instances (office, 3128, no HTTPS, users: alice, bob) | `tests/unit/test_main.py::test_create_instance` | UI: Add Instance modal, fill all fields, submit |
| Create remote instance | POST /api/instances (remote, 3129, HTTPS, users: charlie, dave) | — | UI: Add Instance modal, toggle HTTPS, generate cert, add users |
| Create internal instance | POST /api/instances (internal, 3130, no HTTPS, no users) | — | UI: Add Instance modal, skip Users tab, create |
| List all instances | GET /api/instances returns 3 instances | `tests/integration/test_addon_structure.py::test_list_instances` | UI: Dashboard shows 3 cards (office, remote, internal) |
| Stop remote | POST /api/instances/remote/stop → status = stopped | `tests/unit/test_proxy_manager.py::test_stop_instance` | UI: Dashboard, remote card shows "Stopped" badge, Start button visible |
| Edit office port | PATCH /api/instances/office (port=3128) | `tests/unit/test_main.py::test_update_instance` | UI: Settings modal, General tab, verify port editable |
| Verify isolation | office passwd only has alice/bob, remote has charlie/dave, internal empty | `tests/unit/test_auth_manager.py::test_passwd_isolation` | Terminal: `ls /data/squid_proxy_manager/*/passwd && cat /data/squid_proxy_manager/*/passwd` |
| Delete internal | DELETE /api/instances/internal → instance removed | `tests/unit/test_main.py::test_delete_instance` | UI: Dashboard, internal card gone; confirm modal shown before delete |
| Verify cleanup | /data/squid_proxy_manager/internal directory deleted | `tests/integration/test_addon_structure.py::test_instance_cleanup` | Terminal: `ls /data/squid_proxy_manager/` (internal/ not present) |
| Dashboard updated | GET /api/instances returns 2 instances | — | UI: Dashboard shows 2 cards (office, remote) |

---

### Scenario 6: Certificate Expired, Regenerate

**Goal**: Regenerate cert with longer validity
**Actors**: Admin noticing SSL warnings
**Acceptance Criteria**:
- Current cert expiry visible in HTTPS tab
- Regenerate keeps same CN, updates validity
- New cert generated with correct dates
- Instance restarts with new cert
- HTTPS connectivity verified

| Step | Test Procedure | Automated Test | Manual Check |
|------|---|---|---|
| Open HTTPS tab | GET /api/instances/remote → show cert info | — | UI: Settings modal → HTTPS tab shows "Expires in 300 days" |
| Click Regenerate | POST /api/instances/remote/certs with validity=730 | `tests/unit/test_cert_manager.py::test_regenerate_cert` | UI: "Regenerate Certificate" button, adjust validity to 730 days, click Generate |
| Verify new cert | Old cert and key replaced with new ones | — | Terminal: `ls -la /data/squid_proxy_manager/remote/server.* && openssl x509 -noout -dates -in /data/squid_proxy_manager/remote/server.crt` |
| Check validity | New cert valid for 730 days | — | Terminal: `notAfter - notBefore = 730 days` |
| Instance restarts | Squid process killed and restarted | — | Terminal: `ps aux | grep squid` shows new process |
| Test HTTPS | HTTPS connectivity works | — | `curl --proxy-insecure https://localhost:3129 -U charlie:secret https://example.com` → HTTP 200 |
| No browser warnings | Test in real browser (if available) | `tests/e2e/test_https_ui.py::test_https_no_warnings` | Browser: HTTPS connection shows "valid certificate" or "self-signed" (expected) |

---

### Scenario 7: Start/Stop Without Deleting

**Goal**: Temporarily disable proxy for maintenance
**Actors**: Admin doing maintenance
**Acceptance Criteria**:
- Stop kills Squid process
- Config/users/logs preserved
- Start resumes with same settings
- No data loss

| Step | Test Procedure | Automated Test | Manual Check |
|------|---|---|---|
| Instance running | GET /api/instances/office → status = running | — | UI: Dashboard, office card shows "Running" |
| Stop instance | POST /api/instances/office/stop → status = stopped | `tests/unit/test_proxy_manager.py::test_stop_instance` | UI: Dashboard, office card shows "Stopped", Start button visible |
| Verify Squid killed | Squid process for office not in ps | — | Terminal: `ps aux | grep squid` (office process gone) |
| Verify config preserved | Config file still exists at /data/squid_proxy_manager/office/squid.conf | — | Terminal: `ls /data/squid_proxy_manager/office/squid.conf` (exists) |
| Verify users preserved | Users file still exists with alice/bob | — | Terminal: `cat /data/squid_proxy_manager/office/passwd` (alice/bob present) |
| Start instance | POST /api/instances/office/start → status = running | `tests/unit/test_proxy_manager.py::test_start_instance` | UI: Dashboard, office card shows "Running", Stop button visible |
| Verify Squid restarted | Squid process running on port 3128 | — | Terminal: `ps aux | grep squid \| grep 3128` (process running) |
| Test proxy works | HTTP request with alice credentials | — | `curl -x localhost:3128 -U alice:password123 http://example.com` → HTTP 200 |

---

## Feature-Level Test Coverage

**Mapped to REQUIREMENTS.md**: FR-1 (Instance Mgmt), FR-2 (Auth), FR-3 (HTTPS), FR-4 (UI), FR-5 (API)

### Core Functionality Tests (FR-1)

| Feature | What to Test | Test Type | Expected Result |
|---------|---|---|---|
| Create instance | POST /api/instances with valid name, port | Unit | Instance created, process spawned, config written |
| Create instance (dup name) | POST /api/instances with duplicate name | Unit | Error: "Instance already exists" |
| Create instance (invalid port) | POST /api/instances with port <1024 or >65535 | Unit | Error: "Invalid port" |
| Start instance | POST /api/instances/{name}/start | Unit | Process spawned, status=running |
| Start instance (already running) | POST /api/instances/{name}/start when running | Unit | No error (idempotent), still running |
| Stop instance | POST /api/instances/{name}/stop | Unit | Process killed, status=stopped |
| Stop instance (already stopped) | POST /api/instances/{name}/stop when stopped | Unit | No error (idempotent), still stopped |
| Delete instance | DELETE /api/instances/{name} | Unit | Process killed, dir deleted, no traces |
| List instances | GET /api/instances | Integration | Returns all instances with status |
| Update port | PATCH /api/instances/{name} with new port | Unit | Config updated, instance restarts |
| Update HTTPS toggle | PATCH /api/instances/{name} with https=true/false | Unit | Config updated, cert generated (if true), restarted |

### Authentication Tests (FR-2)

| Feature | What to Test | Test Type | Expected Result |
|---------|---|---|---|
| Add user | POST /api/instances/{name}/users with username/password | Unit | User added to passwd file, hashed |
| Add user (duplicate) | POST /api/instances/{name}/users with existing username | Unit | Error: "User already exists" |
| Add user (invalid chars) | POST /api/instances/{name}/users with invalid username | Unit | Error: "Invalid username" |
| Remove user | DELETE /api/instances/{name}/users/{username} | Unit | User removed from passwd file |
| Remove user (not found) | DELETE /api/instances/{name}/users/nonexistent | Unit | Error: "User not found" |
| Authenticate valid | curl -U username:password to proxy | Integration | HTTP 200 (access allowed) |
| Authenticate invalid password | curl -U username:wrongpass to proxy | Integration | HTTP 407 (auth required) |
| Authenticate no user | curl (no auth header) to proxy | Integration | HTTP 407 (auth required) |
| Instance auth isolation | Users in instance1 cannot auth to instance2 | Integration | Instance1: 200, Instance2: 407 |

### HTTPS Tests (FR-3)

| Feature | What to Test | Test Type | Expected Result |
|---------|---|---|---|
| Generate cert | POST /api/instances/{name}/certs | Unit | Cert and key files created, 0o644 |
| Cert CN param | Generate with CN=test.local | Unit | Cert CN field = test.local |
| Cert validity days | Generate with validity=365 | Unit | Cert notAfter - notBefore = 365 days |
| Cert key size | Generate with key_size=4096 | Unit | Private key is 4096-bit RSA |
| Cert is server type | Check BasicConstraints and ExtendedKeyUsage | Unit | ca=False, EKU contains SERVER_AUTH |
| Cert no ssl_bump | Check Squid config | Unit | Config has "https_port..." but NO "ssl_bump" |
| HTTPS port accessible | HTTPS GET to proxy | Integration | Connection accepted (self-signed ok) |
| HTTPS auth required | HTTPS request without auth | Integration | HTTP 407 |
| HTTPS auth valid | HTTPS request with valid creds | Integration | HTTP 200 |
| Regenerate cert | POST /api/instances/{name}/certs again | Unit | Old cert replaced, new one valid |

### React SPA Frontend Tests (FR-4)

| Feature | What to Test | Test Type | Expected Result |
|---------|---|---|---|
| App renders | Load UI in browser | E2E | Dashboard visible, no errors |
| Instance list loads | GET /api/instances called on load | Frontend Unit | Cards displayed for each instance |
| Add Instance modal opens | Click "Add Instance" button | E2E | Modal appears with tabs (Basic, HTTPS, Users, Test) |
| Add Instance form validates | Try submit with missing name | Frontend Unit | Error shown: "Name required" |
| HTTPS tab visibility | Toggle HTTPS OFF/ON in Add modal | Frontend Unit | Tab appears only when HTTPS=ON |
| Settings modal opens | Click instance card → Settings | E2E | Modal appears with 5 tabs |
| User add form | Fill username/password, click Add | Frontend Unit | User appears in list, no reload |
| User delete | Click delete button on user | Frontend Unit | Confirm modal appears (custom HTML) |
| Confirm modal | Click "Delete" in confirm modal | Frontend Unit | User removed, no page reload |
| Test Proxy button | Click "Test Proxy" in Settings | E2E | Spinner shown, then status (200/error) |
| Auto-refresh logs | Toggle auto-refresh ON | Frontend Unit | Log content updates every 5s |
| Search logs | Type in search box | Frontend Unit | Logs filtered client-side instantly |
| Deep-link safe | Refresh page on /instances/my-proxy/settings | E2E | Page loads correctly (server fallback) |
| Ingress routing | Access via HA ingress path | E2E | Runtime basename detected, routing works |

### Security Tests (NFR-1)

| Feature | What to Test | Test Type | Expected Result |
|---------|---|---|---|
| Non-root container | Check UID/GID in running container | Integration | UID=1000, GID=1000 |
| Dropped capabilities | Check CAP_DROP in config.yaml | Integration | All caps dropped except NET_BIND_SERVICE |
| Read-only filesystem | Try write to root / in running container | Integration | EROFS (read-only fs error) |
| tmpfs /tmp | Check /tmp mount | Integration | tmpfs (temporary, not persisted) |
| Password hashing | Check passwd file format | Unit | Passwords are $apr1$ hashed, not plaintext |
| Secrets not in logs | Check logs for passwords/tokens | CI | No secrets in stdout/stderr |
| Bandit scan | Run bandit on rootfs/app/*.py | CI | 0 HIGH/CRITICAL findings |
| Trivy CVE scan | Scan container image | CI | 0 HIGH/CRITICAL CVEs |

---

## Manual Testing Checklist

Use this checklist for release verification:

### Pre-Release QA (30 min)

- [ ] **Setup**: Create 3 instances (http-only, https, https+auth)
- [ ] **Dashboard**: All 3 visible, status correct, search works
- [ ] **Instance 1 (HTTP)**:
  - [ ] Add 2 users (user1, user2)
  - [ ] Test connectivity: unauthenticated → 407, user1 → 200
  - [ ] Logs: access.log shows requests, auto-refresh works
  - [ ] Stop/Start: config preserved, users still there
- [ ] **Instance 2 (HTTPS)**:
  - [ ] Enable HTTPS, generate cert (CN=proxy.example.com)
  - [ ] Verify cert: CN correct, valid 365 days
  - [ ] Test connectivity: HTTPS proxy works with valid creds
  - [ ] Browser: Self-signed cert shown (expected)
- [ ] **Instance 3 (HTTPS+Auth)**:
  - [ ] HTTPS enabled with cert
  - [ ] Users: alice, bob added
  - [ ] Test: Unauthenticated → 407, alice → 200
  - [ ] Delete instance: confirm dialog, files cleaned
- [ ] **UI Responsiveness**:
  - [ ] Modal tabs work (no page reload)
  - [ ] Add user async spinner shows, inputs disabled
  - [ ] Delete confirm modal (custom HTML, not alert)
  - [ ] Search/filter work instantly
- [ ] **Edge Cases**:
  - [ ] Rename instance (update port, verify old port freed)
  - [ ] Regenerate cert (validity 730 days, verify dates)
  - [ ] Remove user, add again (passwd updated)
- [ ] **Browser Refresh Safety**:
  - [ ] Refresh on /instances/my-proxy/settings (no 404)
  - [ ] Deep-link to /instances works after refresh

---

## Edge Cases & Negative Scenarios

### Invalid Input Handling

| Scenario | Input | Expected Behavior | Automated Test | Manual Check |
|----------|-------|---|---|---|
| Duplicate instance name | POST /api/instances with existing name | Error: "Instance already exists" | `tests/unit/test_proxy_manager.py::test_duplicate_instance` | UI: Error toast shown |
| Missing required field | POST /api/instances without name | Error: "Name is required" | `tests/unit/test_main.py::test_missing_field` | UI: Validation error inline |
| Empty name field | POST /api/instances with name="" | Error: "Name cannot be empty" | — | UI: Submit button disabled |
| Name with special chars | POST with name="proxy@#$%" | Error: "Name contains invalid characters" | `tests/unit/test_proxy_manager.py::test_invalid_name_chars` | — |
| Port out of range | POST with port=80 | Error: "Port must be 3128-3140" | `tests/unit/test_main.py::test_invalid_port_range` | UI: Error shown |
| Port already in use | POST with port=3128 when already taken | Error: "Port 3128 already in use" | `tests/integration/test_proxy_manager.py::test_port_conflict` | — |
| Invalid port (non-numeric) | POST with port="abc" | Error: "Port must be numeric" | — | UI: Input validation (number only) |
| Negative port | POST with port=-1 | Error: "Port must be positive" | — | — |
| Username with spaces | POST /users with username="user name" | Error: "Username cannot contain spaces" | — | UI: Validation error |
| Empty password | POST /users with password="" | Error: "Password cannot be empty" | — | UI: Submit disabled |
| Password too short | POST /users with password="123" | Error: "Password too short (min 8)" (if enforced) | — | UI: Length indicator shown |
| Duplicate username | POST /users/alice when alice exists | Error: "User already exists" | `tests/unit/test_auth_manager.py::test_duplicate_user` | UI: Error shown |
| Delete non-existent user | DELETE /users/nonexistent | Error: "User not found" | — | — |
| Get non-existent instance | GET /api/instances/nonexistent | Error 404: "Instance not found" | — | — |
| Update non-existent instance | PATCH /instances/nonexistent | Error 404: "Instance not found" | — | — |
| Delete non-existent instance | DELETE /instances/nonexistent | Error 404: "Instance not found" | — | — |
| Invalid cert CN | POST /certs with CN="" | Error: "CN cannot be empty" | — | UI: Validation error |
| Invalid cert validity | POST /certs with validity=0 | Error: "Validity must be > 0" | — | UI: Validation error |
| Invalid cert validity (too large) | POST /certs with validity=100000 | Error: "Validity too large (max 3650)" | — | UI: Validation error |
| Invalid key size | POST /certs with key_size=1024 | Error: "Key size must be 2048 or 4096" | — | UI: Dropdown only shows valid options |

### Boundary Conditions

| Scenario | Condition | Expected Behavior | Automated Test | Notes |
|----------|-----------|---|---|---|
| Min valid port | Create instance with port=3128 | Success, instance created | — | First allowed port |
| Max valid port | Create instance with port=3140 | Success, instance created | — | Last allowed port |
| Port 3128-3140 exhausted | Create 13 instances (all ports taken) | 13th create fails: "No ports available" | — | Test resource exhaustion |
| Very long instance name | POST with name=500-char string | Accept (or truncate to limit, e.g., 255 chars) | — | Verify DB/FS can handle |
| Very long username | POST /users with username=255 chars | Accept (or enforce reasonable limit) | — | Verify passwd file handling |
| Very long password | POST /users with password=1000 chars | Accept (hash works correctly) | — | Verify htpasswd can hash |
| Cert validity = 1 day | POST /certs with validity=1 | Success, cert expires in 24h | — | Edge of valid range |
| Cert validity = 3650 days | POST /certs with validity=3650 | Success, cert expires in 10 years | — | Upper boundary |
| Many users (100+) | Add 100 users to instance | All users listed/queryable | — | Performance/UX check |
| Many logs (1GB+) | Generate large access.log | UI can still display/search without hanging | — | Pagination or tail needed? |
| Empty access.log | Logs tab with no activity | Show "No log entries" or empty message | — | UI gracefully handles empty |
| Renamed instance (name length 1) | Create with name="a" | Success | — | Minimum valid name |
| Instance name = reserved word | Create with name="api" or "admin" | Accept (not reserved in this context) | — | No conflicts with routes |

### Concurrent & Race Conditions

| Scenario | Condition | Expected Behavior | Automated Test | Notes |
|----------|-----------|---|---|---|
| Simultaneous create | POST /instances twice with same name (parallel) | One succeeds, one fails "already exists" | — | Race condition handling |
| Delete while stopping | DELETE /instances/{name} during POST .../stop | Graceful: either completes stop then delete, or deletes immediately | — | State machine robustness |
| Start while creating | POST .../start before POST /instances completes | Error: "Instance not yet ready" or "Instance not found" | — | Initialization order |
| Add user during add user | Two parallel POST .../users requests | Both succeed (no collision), both users in passwd | — | File locking or transactions |
| Regenerate cert during start | POST .../certs during POST .../start | Restart uses new cert (no corruption) | — | File sync verification |
| Stop twice rapidly | POST .../stop, then POST .../stop immediately | First succeeds, second is idempotent (no error) | — | Idempotence verification |
| Start twice rapidly | POST .../start, then POST .../start immediately | First spawns process, second is idempotent (no error) | — | Process spawn protection |
| Modify instance during delete | PATCH /instances/{name} while DELETE in progress | DELETE wins (instance removed), PATCH fails "not found" | — | Atomic deletion |
| Download log while log rotating | GET /logs during access.log rotation | Either returns old or new content, no corruption | — | File handle safety |

### Resource Exhaustion & Error Recovery

| Scenario | Condition | Expected Behavior | Automated Test | Notes |
|----------|-----------|---|---|---|
| Disk full | Create instance when /data nearly full | Error: "Insufficient disk space" | — | Graceful OOM handling |
| Permission denied | Data dir has no write permission | Error: "Permission denied" | — | File system error handling |
| Squid binary missing | Squid executable deleted/moved | Error on start: "Squid binary not found" | `tests/integration/test_addon_structure.py::test_squid_binary_missing` | Container should have it; test robustness |
| Config file corrupted | Manually corrupt squid.conf | Squid fails to start, error in logs | — | Config validation before start |
| Passwd file corrupted | Manually corrupt passwd file (invalid hash) | Auth fails gracefully, error in logs | — | Validation on read |
| Cert file deleted | Delete server.crt while instance running | Squid continues (existing connection), restart fails | — | Hot-reload edge case |
| Out of memory | Large concurrent connections | Graceful degradation or error response, not OOM kill | — | Container memory limits help here |
| Too many open files | Max file descriptors exceeded | Error: "Too many open files" | — | Limits set in container |

### Invalid State Transitions

| Scenario | Invalid Operation | Expected Behavior | Automated Test | Notes |
|----------|---|---|---|---|
| Enable HTTPS twice | PATCH /instances with https=true when already true | Idempotent: succeeds, no-op (or regenerates cert) | — | Should be safe |
| Disable HTTPS while running | PATCH /instances with https=false while running | Update config, restart instance without HTTPS | — | Clean state transition |
| Delete running instance | DELETE /instances/{name} when running | Process killed, all files deleted | `tests/unit/test_proxy_manager.py::test_delete_running` | Should handle gracefully |
| Stop stopped instance | POST /instances/{name}/stop when already stopped | Idempotent: no error, still stopped | `tests/unit/test_proxy_manager.py::test_stop_idempotent` | Already tested above |
| Start running instance | POST /instances/{name}/start when running | Idempotent: no error, still running | `tests/unit/test_proxy_manager.py::test_start_idempotent` | Already tested above |
| Remove user during auth | DELETE /users/{username} during live request | User removed from future requests, current request may succeed or fail (depends on timing) | — | Race condition edge case |
| Change port of running instance | PATCH /instances with new port while running | Stop with old port, start with new port (restart) | — | Verify port freed |
| Update instance name | PATCH /instances/{name} with new name | Error: "Instance name cannot be changed" (or allow + move data) | — | Clarify UX requirement |

### UI/Frontend Error Scenarios

| Scenario | User Action | Expected Behavior | Automated Test | Manual Check |
|----------|---|---|---|---|
| Submit Add modal with no changes | Open Add modal, click Create without filling anything | Validation errors shown inline, submit button disabled | `tests/unit/test_main.py::test_form_validation` | UI: Red error text below fields |
| Close modal during async add | Open Add Instance, click Create, immediately close modal | Request still pending in background (or cancel request) | — | UI: Loading spinner blocked close button? |
| Delete with accidental double-click | Click delete button twice rapidly | Confirm modal shown once, delete once | — | Button disabled during request |
| Test Proxy timeout | Click Test Proxy, proxy doesn't respond within 5s | Show "Connection timeout" error, not hang | `tests/e2e/test_full_flow.py::test_timeout` | UI: Timeout message shown |
| Test Proxy network error | Click Test Proxy, network unreachable | Show "Network error" or specific error message | — | UI: Error toast shown |
| Network disconnect during list | GET /api/instances with network down | Error loading instances, retry button shown | — | UI: Error state + retry |
| Logs search no results | Search for non-existent IP in logs | Show "No results found" (not error) | — | UI: Empty state message |
| Very large log viewer | Try to display 1GB log file | Graceful: show last N lines (e.g., 1000) or paginate | — | Performance test needed |
| Auto-refresh disabled but manual refresh | Disable auto-refresh, manually click refresh | Logs updated instantly | — | Manual reload works |
| Sort logs by column | Click column header to sort | Logs re-sorted (if sort implemented) | — | UI usability |
| Browser back button | On Settings modal, click browser back | Modal closed, return to dashboard | `tests/e2e/test_https_ui.py::test_browser_back` | Navigation UX |
| Session timeout | Page open >30 min, no activity | Graceful re-auth or error, not silent failure | — | HA auth token handling |

### Authentication Edge Cases

| Scenario | Condition | Expected Behavior | Automated Test | Notes |
|----------|-----------|---|---|---|
| Auth with spaces in username | username="alice " (trailing space) | Trim spaces and match, or reject | — | Password manager edge case |
| Auth with spaces in password | password="pass word" (space in middle) | Accept (spaces are valid in passwords) | — | Verify htpasswd supports | <!-- pragma: allowlist secret -->
| Case-sensitive username | Add "Alice", try auth as "alice" | Auth fails (usernames case-sensitive) | — | Clarify UX requirement |
| Case-sensitive password | Add user with "Password123", try "password123" | Auth fails (passwords case-sensitive) | — | Standard behavior |
| Special chars in password | password="p@ss!w0rd#%^" (test example, not real) | Accept and hash correctly | `tests/integration/test_e2e_flows.py::test_special_chars_auth` | Verify htpasswd escaping | <!-- pragma: allowlist secret -->
| Unicode username | username="用户" (Chinese chars) | Accept or reject (depends on requirements) | — | Squid compatibility check |
| Unicode password | password="パスワード" (Japanese) | Accept and hash correctly | — | UTF-8 support verify |
| Very long credentials | username/password 1000 chars | Accept and authenticate (htpasswd handles) | — | Boundary test |
| Null bytes in password | password with null bytes (test example) | Reject or truncate safely | — | Security edge case | <!-- pragma: allowlist secret -->
| Empty username after trim | username="   " (only spaces) | Reject: "Username cannot be empty" | — | Validation |
| Auth with wrong instance | User added to instance1, try on instance2 | Auth fails: 407 (users isolated per-instance) | `tests/integration/test_e2e_flows.py::test_auth_isolation` | Verify isolation |

### Certificate Edge Cases

| Scenario | Condition | Expected Behavior | Automated Test | Notes |
|----------|-----------|---|---|---|
| Cert CN with spaces | CN="My Proxy Server" | Accept and include in cert | — | Display in cert details |
| Cert CN with special chars | CN="proxy-1.example.com:3128" | Accept (or sanitize special chars) | — | Verify cert formatting |
| Cert CN = IP address | CN="192.168.1.1" | Accept and create cert with CN=IP | — | IP cert validity (browsers may reject) |
| Cert country code invalid | Country="USA" (3 chars) | Error: "Country code must be 2 chars (e.g., US)" | — | ISO 3166-1 alpha-2 validation |
| Cert org name empty | Org="" | Accept (optional field) or error (required field) | — | Clarify requirement |
| Generate cert, then immediately delete instance | POST /certs, then DELETE /instances | Delete waits for cert gen to complete, then deletes cert | — | Transaction safety |
| Generate same cert twice | POST /certs, then POST /certs (same params) | Succeeds, old cert replaced (no error) | — | Idempotence |
| Cert validity = 0 | POST /certs with validity=0 | Error: "Validity must be > 0 days" | — | Already covered above |
| Cert with past notBefore | Manual cert with past date | Squid may reject or accept (test both) | — | Edge case for manual certs |
| Cert with future notBefore | POST /certs with start_date=tomorrow (if supported) | Cert valid from tomorrow onwards | — | Advanced use case |
| Regenerate cert while instance running | Instance running on HTTPS, POST /certs | New cert generated, instance restarts, HTTPS still works | — | Zero-downtime? Or brief downtime? |
| Cert size 2048 vs 4096 | Create two instances with different key sizes | Both work (performance difference noted) | — | Benchmark performance |
| Download cert from UI (if feature exists) | GET /api/instances/{name}/cert | Return certificate file (PEM format) | — | Useful for client-side trust |

---

## CI/CD Test Gates

All gates must pass before release:

| Gate | Tool | Command | Failure = Blocker |
|------|------|---------|-------------------|
| Lint (Python) | ruff + black | `ruff check squid_proxy_manager/` | Yes |
| Lint (Frontend) | prettier + eslint | `npm run lint` | Yes |
| Type check | Pylance + TypeScript | `mypy squid_proxy_manager/` | Yes |
| Security (Python) | bandit | `bandit -r squid_proxy_manager/rootfs/app/` | Yes |
| Security (Container) | Trivy | `trivy image squid-proxy-manager:latest` | Yes |
| Unit + Integration | pytest | `pytest tests/unit tests/integration` | Yes |
| E2E (Browser) | Playwright | `pytest tests/e2e` | Yes |
| Coverage | pytest-cov | `pytest --cov=squid_proxy_manager --cov-fail-under=80` | No (warning) |

---

---

## Document Alignment Reference

**See REQUIREMENTS.md for**:
- Functional Requirements (FR-1 to FR-5): What features exist
- User Scenarios (1-7): What users do with the system
- Non-Functional Requirements (NFR-1 to NFR-4): Quality attributes
- Known Issues & Fixes: Root causes (prevent regression)
- Architecture Decisions: Why design choices were made

**This Document (TEST_PLAN.md) Provides**:
- Test Procedures for each user scenario (8 scenarios × steps → acceptance criteria)
- Automated Test References: pytest test file paths
- Manual Check Steps: terminal commands and UI actions
- Feature-Level Coverage: FR-1 through FR-4 test matrices
- Edge Cases & Negative Scenarios: 10 subsections covering error conditions
- CI/CD Gates: Release-blocking test requirements
- Manual QA Checklist: 30-min pre-release verification

---

## How to Read This Document

1. **Want to test user workflow?** → Go to "User Scenario Testing" section (7 scenarios)
2. **Want to test specific feature?** → Go to "Feature-Level Test Coverage" (Core Functionality, Auth, HTTPS, Frontend, Security)
3. **Looking for error/edge case?** → Go to "Edge Cases & Negative Scenarios" (invalid inputs, race conditions, resource exhaustion)
4. **About to release?** → Go to "Manual Testing Checklist" (30-min QA) and "CI/CD Test Gates" (requirements)

## Test Maintenance

**When scenario changes in REQUIREMENTS.md**:
- Update corresponding TEST_PLAN.md scenario section
- Adjust test procedures, acceptance criteria, test references
- Rebuild relevant feature-level test coverage rows

**When feature added to REQUIREMENTS.md**:
- Create new FR entry with description
- Add entry to Feature-Level Test Coverage table (Core Functionality, Auth, HTTPS, Frontend, or Security)
- Add edge case rows to "Edge Cases & Negative Scenarios" if applicable
- Commit with cross-reference: "test: add {feature} coverage (refs REQUIREMENTS.md FR-X)"

**When bug fixed**:
- Check REQUIREMENTS.md "Known Issues & Fixes"
- Verify test in TEST_PLAN.md prevents regression
- If no test exists, add it to Feature-Level Coverage or Edge Cases
- Commit: "fix: {issue} (test: {test file}::test_name)"
