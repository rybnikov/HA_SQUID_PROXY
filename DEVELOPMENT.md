# Development Guide: HA Squid Proxy Manager

**Latest Update**: Comprehensive workflows for features, bugs, and frontend troubleshooting using Playwright MCP.

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [Development Workflows](#development-workflows)
3. [Adding Features](#adding-features)
4. [Reporting & Fixing Bugs](#reporting--fixing-bugs)
5. [Frontend & UI Troubleshooting](#frontend--ui-troubleshooting)
6. [Testing Guide](#testing-guide)
7. [IDE Setup](#ide-setup)
8. [Common Issues & Debugging](#common-issues--debugging)
9. [Technical Reference](#technical-reference)
10. [Release Process](#release-process)

---

## Initial Setup

### System Requirements

- **OS**: macOS, Linux, or Windows (WSL2)
- **Docker**: Latest version (includes Docker Compose)
- **Node.js**: v18+ (for frontend development)
- **Git**: Latest version

### Automated Setup

Run the environment setup script for your OS:

```bash
# macOS / Linux
./setup_dev.sh

# Windows (PowerShell)
./setup_dev.ps1
```

**What gets installed**:
- Docker validation (pre-requisite)
- Node.js + npm packages (frontend tooling)
- Pre-commit hooks (git integration)
- Test containers (unit, integration, E2E)

**What you don't need**:
- ❌ Python venv (all Python runs in Docker)
- ❌ Local system packages (everything containerized)
- ❌ Manual tool installation (setup scripts handle it)

### Manual Setup (If Scripts Fail)

```bash
# 1. Install Docker (https://docs.docker.com/get-docker/)
# 2. Install Node.js + npm (https://nodejs.org/)
# 3. Clone repo
git clone <repo> && cd HA_SQUID_PROXY

# 4. Install frontend dependencies
npm install --prefix squid_proxy_manager/frontend

# 5. Build test containers
docker compose -f docker-compose.test.yaml --profile unit build test-runner

# 6. Verify setup
./run_tests.sh unit
```

### Local Addon Testing

Run the addon container locally for manual testing:

```bash
# Start addon on default port 8099
./run_addon_local.sh start

# Start on custom port
./run_addon_local.sh start --port 8100

# View logs (follow mode)
./run_addon_local.sh logs

# Restart addon
./run_addon_local.sh restart

# Open shell in running container
./run_addon_local.sh shell

# Show container status
./run_addon_local.sh status

# Stop addon
./run_addon_local.sh stop

# Clean up container and data
./run_addon_local.sh clean
```

**Access URLs:**
- Web UI: http://localhost:8099
- API: http://localhost:8099/api
- Health check: http://localhost:8099/health

**Data & Logs:**
- Data directory: `.local/addon-data/` (persists between runs)
- Logs: `.local/addon-logs/`

---

---

## Security & Quality Focus

### Security-First Development

This project prioritizes security at every stage. **Security issues block releases.**

**Key Security Principles**:
1. **No secrets in code**: Passwords, tokens, API keys never in git (use .env or config)
2. **Non-root containers**: Always run as UID 1000:1000 (verified in tests)
3. **Dropped capabilities**: CAP_DROP all except NET_BIND_SERVICE (verified in CI)
4. **Read-only filesystem**: Root filesystem immutable, only /tmp, /run writable (verified in tests)
5. **Hashed credentials**: MD5-crypt (APR1) for passwords, never plaintext (verified in tests)
6. **Input validation**: All API inputs validated before use (no SQL injection, command injection, etc.)
7. **Least privilege**: Squid runs as non-root, limited file access (verified in tests)

**Security Testing (CI/CD Gates - All Must Pass)**:

| Gate | Tool | Command | Failure = Release Block |
|------|------|---------|---|
| **Python Security** | bandit | `bandit -r squid_proxy_manager/rootfs/app/` | YES |
| **Container CVEs** | Trivy | `trivy image squid-proxy-manager:latest` | YES (HIGH/CRITICAL) |
| **Dependencies** | pip-audit | `pip-audit -r requirements.txt` | YES (if in CI) |
| **Secrets Scan** | truffleHog | `trufflehog filesystem .` | YES |

**Before You Commit**:
```bash
# Check for secrets
trufflehog filesystem . --fail-verified --json | jq .

# Check Python security
bandit -r squid_proxy_manager/rootfs/app/

# Check container for CVEs (after building)
trivy image squid-proxy-manager:latest --severity HIGH,CRITICAL
```

### Code Quality Standards

**Quality is enforced by CI/CD. All checks must pass before merge.**

**Linting & Formatting (Automated Fixes)**:

| Tool | Language | Config | Auto-Fix |
|------|----------|--------|----------|
| **Black** | Python | `pyproject.toml` | Yes: `black squid_proxy_manager/` |
| **Ruff** | Python | `pyproject.toml` | Yes: `ruff check --fix squid_proxy_manager/` |
| **Prettier** | JS/TS/JSON | `.prettierrc` | Yes: `npm run format` |
| **ESLint** | TypeScript | `eslint.config.js` | Yes: `npm run lint:fix` |

**Type Checking (Must Fix)**:

| Tool | Language | Command | Must Pass |
|------|----------|---------|-----------|
| **MyPy** | Python | `mypy squid_proxy_manager/` | YES |
| **TypeScript** | TypeScript | `npm run build --prefix frontend` | YES |

**Test Coverage (Target: >80%)**:

```bash
# Run with coverage report
./run_tests.sh  # Generates htmlcov/index.html

# View coverage
open htmlcov/index.html

# Coverage gates (CI blocks if <80%):
# - Core modules: >90%
# - Feature modules: >80%
# - UI tests: >75%
```

**Pre-Commit Checks** (automatic on `git commit`):

```bash
# Install hooks
pre-commit install

# Manual run
pre-commit run --all-files

# Bypasses (ONLY for documentation, not code)
git commit --no-verify
```

**Code Review Checklist** (Before approving PR):

- [ ] **Security**: No secrets, no privilege escalation, validated inputs
- [ ] **Tests**: All tests passing, new tests added, >80% coverage
- [ ] **Quality**: Linting passes, types correct, no TODOs without issues
- [ ] **Documentation**: REQUIREMENTS.md, TEST_PLAN.md, README.md updated
- [ ] **Performance**: No N+1 queries, O(n) loops, intentional sleeps (with reason)
- [ ] **Backwards Compatibility**: No breaking API changes (or major version bump)

---

## Development Workflows

### Quick Reference

**Adding a feature**: [See "Adding Features"](#adding-features)
**Fixing a bug**: [See "Reporting & Fixing Bugs"](#reporting--fixing-bugs)
**Frontend issue**: [See "Frontend & UI Troubleshooting"](#frontend--ui-troubleshooting)
**Ready to release**: [See "Release Process"](#release-process)

**Security checks**: `bandit`, `trivy`, `trufflehog` (run before pushing)
**Quality checks**: `black`, `ruff`, `prettier`, `eslint`, `mypy` (auto-fixed or blocked by CI)
**Test quality**: >80% coverage, all suites passing (release gate)

---

## Adding Features

### Step 1: Plan & Document

**Before writing code**, update REQUIREMENTS.md:

1. Open [REQUIREMENTS.md](REQUIREMENTS.md)
2. Add to appropriate **FR section** (FR-1 through FR-5):
   ```markdown
   ### FR-X: [New Feature Name]
   - [Requirement 1]
   - [Requirement 2]
   ```
3. Add **User Scenario** (if user-facing):
   ```markdown
   ### Scenario N: [User Goal]
   **Actor**: [Who uses it]
   **Goal**: [What they want]
   **Steps**:
   1. [Step 1]
   2. [Step 2]
   ...
   ```
4. Commit: `docs: add FR-X requirements (feature: {name})`

### Step 2: Design & Discuss

**For UI/Frontend changes**, use Playwright MCP for visual verification:

```bash
# 1. Create design mockup (Figma or quick React component)
# 2. Use Playwright to verify component behavior
npm run test:ui -- --watch

# 3. Take screenshots with Playwright MCP
# - Inspect elements: right-click → "Inspect with Playwright"
# - Record interactions: "Record Playwright Test"
# - Verify responsive design: Device emulation
```

**For API/Backend changes**, discuss in code comments:
- Link to REQUIREMENTS.md requirement
- Explain why design was chosen
- Reference any known issues or edge cases

### Step 3: Implement Feature

#### Backend (Python - squid_proxy_manager/rootfs/app/)

```bash
# 1. Create feature branch
git checkout -b feature/proxy-feature-name

# 2. Implement:
# - Update proxy_manager.py (add method)
# - Update main.py (add API endpoint)
# - Update squid_config.py or auth_manager.py (if needed)

# 3. Add tests FIRST:
# - Unit test: tests/unit/test_proxy_manager.py::test_new_feature
# - Integration test: tests/integration/test_e2e_flows.py::test_real_feature
# - Make tests fail first (TDD), then implement

# 4. Run tests
./run_tests.sh unit

# 5. Commit with test reference
git commit -m "feat: implement proxy feature
- Feature: [description]
- Tests: tests/unit/test_proxy_manager.py::test_new_feature
- Docs: REQUIREMENTS.md FR-X"
```

#### Frontend (React - squid_proxy_manager/frontend/src/)

```bash
# 1. Create feature branch
git checkout -b feature/ui-feature-name

# 2. Implement in feature-based structure:
# squid_proxy_manager/frontend/src/
# ├── features/[feature-name]/
# │   ├── [Feature]Component.tsx
# │   └── tests/
# │       └── [Feature]Component.test.tsx
# └── ui/[reusable]/
#     └── [Component].tsx

# 3. Add tests FIRST:
npm run test -- features/feature-name --watch

# 4. Verify with E2E (later)
./run_tests.sh e2e

# 5. Format & lint
npm run lint:fix
npm run format

# 6. Commit
git commit -m "feat(ui): add feature component
- Component: [name] with [capabilities]
- Tests: features/feature-name/tests/
- Design: [Figma link or description]"
```

### Step 4: Test Coverage

**Add test row to TEST_PLAN.md**:

1. Open [TEST_PLAN.md](TEST_PLAN.md)
2. Find matching "Feature-Level Test Coverage" section:
   - Core Functionality (FR-1)
   - Authentication (FR-2)
   - HTTPS (FR-3)
   - Frontend (FR-4)
   - Security (NFR-1)
3. Add row:
   ```markdown
   | Feature name | Test description | Test Type | Expected result |
   |---|---|---|---|
   | New feature | POST /api/new with params | Unit | Success, data persisted |
   ```
4. Mark status: `✅` (passing) or `[ ]` (pending)

### Step 5: Documentation

**Update relevant docs**:

1. **REQUIREMENTS.md**: Already updated in Step 1
2. **TEST_PLAN.md**: Updated in Step 4
3. **DEVELOPMENT.md** (this file): Add troubleshooting if new commands/patterns
4. **README.md**: If user-facing, add usage example

### Step 6: Code Review & Merge

```bash
# 1. Run full test suite
./run_tests.sh

# 2. Create pull request with:
# - Feature description (link REQUIREMENTS.md FR-X)
# - Test coverage (TEST_PLAN.md section)
# - Screenshots (if UI change, use Playwright MCP)
# - Manual test steps

# 3. After review: merge to main
git checkout main && git pull origin main
git merge feature/feature-name
git push origin main
```

---

## Reporting & Fixing Bugs

### Step 1: Create Issue with Details

Use this template:

```markdown
## Issue: [Brief Title]

**Component**: Backend / Frontend / Docker / Tests

**Steps to Reproduce**:
1. [Action 1]
2. [Action 2]
3. [Observed behavior]

**Expected Behavior**:
[What should happen]

**Actual Behavior**:
[What actually happened]

**Error Output** (if applicable):
[Full error log or screenshot]

**Environment**:
- OS: [macOS / Linux / Windows]
- Docker: [version]
- Browser: [Chrome / Firefox / Safari] (if UI issue)

**Related REQUIREMENTS.md**:
[FR-X or Scenario N if applicable]
```

### Step 2: Reproduce & Root Cause

```bash
# 1. Try to reproduce
./run_tests.sh unit

# 2. If integration issue:
docker compose -f docker-compose.test.yaml --profile unit run --rm test-runner bash
# Inside container, manually test or inspect files

# 3. If frontend issue:
npm run dev      # Start local dev server (if possible)
npm run test:ui  # Run visual tests

# 4. Check logs
docker compose -f docker-compose.test.yaml logs addon
docker compose -f docker-compose.test.yaml exec addon cat /data/squid_proxy_manager/logs/*/cache.log
```

### Step 3: Write Failing Test

**Before fixing**, add test that reproduces issue:

```bash
# Backend
git checkout -b fix/bug-name
# Add test to tests/unit/test_proxy_manager.py or tests/integration/test_e2e_flows.py
# Test should FAIL initially
./run_tests.sh unit

# Frontend
# Add test to squid_proxy_manager/frontend/src/features/*/tests/
npm run test -- features/feature-name --watch
# Test should FAIL initially
```

### Step 4: Fix Code

```bash
# Make minimal changes to fix issue
# Reference test file in code comments:
# ✓ Test: tests/unit/test_proxy_manager.py::test_bug_fix

# Verify fix
./run_tests.sh unit
npm run test
```

### Step 5: Add Regression Prevention

**Update REQUIREMENTS.md "Known Issues & Fixes"**:

```markdown
### vX.Y.Z: [Brief Issue Title]
**Issue**: [User-visible problem]
**Root Cause**: [Why it happened]
**Fix**: [Code/config change]
**Test**: `tests/unit/test_proxy_manager.py::test_name` or `tests/integration/...`
```

### Step 6: Document & Commit

```bash
# Commit with bug fix details
git commit -m "fix: issue title

- Issue: [brief description]
- Root cause: [why]
- Fix: [what changed in code]
- Tests: tests/unit/test_name
- Docs: REQUIREMENTS.md Known Issues section"

# Push and create PR
git push origin fix/bug-name
```

---

## Frontend & UI Troubleshooting

### Using Playwright MCP for Design Issues

**Playwright MCP** helps inspect, debug, and verify UI components without leaving your editor.

#### Common Workflow: Modal Not Showing

```bash
# 1. Start dev server (if available)
npm run dev

# 2. Open browser DevTools
# OR use Playwright MCP in your IDE:
# - VS Code: Ctrl+Shift+P → "Playwright: Record Test"
# - OR: Right-click element → "Inspect with Playwright"

# 3. Record interaction:
# - Click "Add Instance" button
# - Observe modal opens (or fails)
# - Export as test

# 4. If modal missing in real test:
# - Check React component: features/instances/AddInstanceModal.tsx
# - Verify conditional rendering: {showModal && <Modal />}
# - Check CSS: ui/Modal.css for visibility (display: block, z-index)
# - Run: npm run test -- features/instances --watch
# - Use Playwright to visually inspect in browser

# 5. Fix & verify
npm run test -- features/instances --watch
./run_tests.sh e2e
```

#### Common Workflow: Form Validation Not Working

```bash
# 1. Inspect form element
# - Playwright: Right-click input → "Inspect with Playwright"
# - Check HTML: <input type="text" required value="" />

# 2. Check React logic
# - Open features/instances/AddInstanceForm.tsx
# - Verify onChange handler: setName(e.target.value)
# - Verify validation: {errors.name && <span>Error</span>}
# - Verify submit: disabled={!isFormValid}

# 3. Test in browser
npm run dev
# Try submitting form with empty fields

# 4. Run unit test
npm run test -- features/instances --watch
# If test fails: fix component logic

# 5. E2E verification
./run_tests.sh e2e
```

#### Common Workflow: API Response Not Showing in UI

```bash
# 1. Check Network tab
# - Playwright MCP: Use "Network" panel in Inspector
# - OR: Browser DevTools (F12) → Network tab
# - Look for GET /api/instances request
# - Check response: 200 OK with correct data

# 2. If API fails:
# - Backend issue: See "Reporting & Fixing Bugs"
# - Run integration test: ./run_tests.sh unit

# 3. If API succeeds but UI doesn't update:
# - Check React Query / state management
# - features/instances/InstanceList.tsx:
#   ```tsx
#   const { data: instances } = useQuery({
#       queryKey: ['instances'],
#       queryFn: () => fetch('/api/instances').then(r => r.json())
#   });
#   ```
# - Verify: data !== null before rendering
# - Check CSS: not hidden (display: none, visibility: hidden)

# 4. Test fix
npm run test -- features/instances --watch
./run_tests.sh e2e
```

#### Using Playwright Inspector for Assertions

```bash
# 1. Record test with Playwright
npm run test:ui

# 2. Use Inspector to build selectors:
# - Hover over element → Copy selector
# - Verify selector matches expected element

# 3. Build assertion:
# await expect(page.locator('button:has-text("Add Instance")')).toBeVisible();

# 4. Run test
npm run test -- specific-test.test.ts
```

### Frontend Linting & Format

```bash
# Check for issues
npm run lint

# Auto-fix linting errors
npm run lint:fix

# Format code with Prettier
npm run format

# Run type checking
npm run typecheck
```

---

---

## Quality Assurance Philosophy

### Why We Test Heavily

1. **Security**: Tests verify non-root, dropped caps, read-only fs, password hashing
2. **Reliability**: Tests catch regressions before users see them
3. **Maintainability**: Tests document how features should work
4. **Docker-First**: Real Squid binary in containers = confidence in production behavior

### Testing Pyramid

```
     E2E (10)                ← Real browser + addon
    /       \
   /         \
  /           \             ← Real Squid container
 /     Int     \            ← ~20 tests
/               \
-----------------           ← Unit (40+)
 Unit Tests     ← Mocked, fastest, highest count
```

### Test Quality Gates (Release Blocking)

**All of these must pass to deploy**:

1. ✅ **Unit Tests**: 40+ tests, all passing
2. ✅ **Integration Tests**: 20+ tests with real Squid, all passing
3. ✅ **E2E Tests**: 10+ browser tests, all passing
4. ✅ **Security Tests**: Bandit (0 HIGH), Trivy (0 HIGH/CRITICAL), Trufflehog (0 verified)
5. ✅ **Type Checking**: MyPy + TypeScript strict, 0 errors
6. ✅ **Code Coverage**: >80% across core modules
7. ✅ **Linting**: Black, Ruff, Prettier, ESLint, 0 issues

**If any gate fails**: Code doesn't merge. No exceptions. Fix it.

### Test Data & Scenarios

**See TEST_PLAN.md for**:
- 7 user scenarios with step-by-step test procedures
- 40+ feature-level tests (core, auth, HTTPS, frontend, security)
- 100+ edge cases (invalid inputs, race conditions, errors)
- Manual QA checklist (30 min pre-release)

---

## Testing Guide

### Test Architecture

**Unit Tests** (40 tests)
- Auth Manager (10 tests): User management, password hashing
- Certificate Manager (6 tests): Cert generation, validity, permissions
- Input Validation (8 tests): Instance names, ports, usernames
- Proxy Manager (5 tests): Instance lifecycle
- Squid Config (6 tests): Config generation, HTTPS setup
- HTTPS Configuration (5 tests): Critical NO ssl_bump bug detection

**Integration Tests** (60 tests)
- API endpoints: GET, POST, DELETE operations
- Server startup and initialization
- Ingress compatibility: Home Assistant path normalization
- Real Squid container tests
- HTTPS certificate handling
- Process lifecycle and cleanup
- File permissions and structure validation
- Concurrent operations
- Error handling and logging

**E2E Tests** (37 tests, fully parallelizable)
- 7 user scenarios from REQUIREMENTS.md
- 10 HTTPS feature lifecycle tests
- 12+ edge cases and error conditions
- Browser UI interactions with Playwright
- Critical: test_https_critical_no_ssl_bump validates NO ssl_bump bug

**Frontend Tests** (Vitest)
- React component unit tests
- UI rendering and interactions

### E2E Testing Architecture

**Design Principles**

✅ **Pure End-to-End** (NO MOCKS)
- All E2E tests run against real Docker containers
- Real addon instance with actual Squid proxies
- Real database (instance files stored in `/data/`)
- Real browser automation via Playwright (chromium)

✅ **Docker-First Execution**
- E2E tests **never** run locally
- All tests run in `e2e-runner` container (Python 3.11 + Playwright)
- Tests connect to `addon` container (real HA addon) via HTTP
- Addon container spawns real Squid instances via subprocess.Popen

✅ **UI Scenario Testing**
- Playwright tests interact with real UI (HTML/CSS/JavaScript)
- Test workflows: button clicks, form fills, modal confirmations
- Test all 7 user scenarios from REQUIREMENTS.md
- Verify UI feedback (error messages, loading states, modal visibility)

**Architecture Diagram**

```
┌─────────────────────────────────────────────┐
│ Docker Compose Stack (tests/docker-compose.test.yaml) │
├─────────────────────────────────────────────┤
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ e2e-runner Container (Python 3.11)   │   │
│  ├──────────────────────────────────────┤   │
│  │ · pytest (test runner)                │   │
│  │ · Playwright (browser automation)     │   │
│  │ · aiohttp (HTTP client)               │   │
│  │ · Executes: tests/e2e/*.py            │   │
│  │ · Command: pytest tests/e2e -n 3     │   │
│  └────────────┬─────────────────────────┘   │
│               │                              │
│               │ HTTP to http://addon:8099   │
│               ↓                              │
│  ┌──────────────────────────────────────┐   │
│  │ addon Container (HA Addon)            │   │
│  ├──────────────────────────────────────┤   │
│  │ · main.py (aiohttp server on :8099)   │   │
│  │ · proxy_manager.py (lifecycle)        │   │
│  │ · Real squid binary (/usr/sbin/squid) │   │
│  │ · Port mapping: 3200-3210 → host      │   │
│  └────────────┬─────────────────────────┘   │
│               │                              │
│               │ subprocess.Popen spawns     │
│               ↓                              │
│  ┌──────────────────────────────────────┐   │
│  │ Squid Processes (Real instances)      │   │
│  ├──────────────────────────────────────┤   │
│  │ · Port 3200: Instance 1 (parallel)    │   │
│  │ · Port 3201: Instance 2 (parallel)    │   │
│  │ · Port 3202: Instance 3 (parallel)    │   │
│  │ · Config: /data/instance-name/squid.  │   │
│  │ · Auth: /data/instance-name/passwd    │   │
│  │ · HTTPS: /data/instance-name/*.crt/   │   │
│  └──────────────────────────────────────┘   │
│                                              │
└─────────────────────────────────────────────┘
```

**Execution Flow**

1. `docker compose -f docker-compose.test.yaml --profile e2e build`
   - Builds e2e-runner image (tests/Dockerfile.test)
   - Builds addon image (squid_proxy_manager/Dockerfile)

2. `docker compose -f docker-compose.test.yaml --profile e2e up --abort-on-container-exit --exit-code-from e2e-runner`
   - Starts addon container first (health check: curl /health)
   - Starts e2e-runner container
   - e2e-runner depends_on addon (waits for health check)

3. Inside e2e-runner:
   ```
   pytest tests/e2e -v --tb=short -n 3 --dist=loadscope
   ```
   - Spawns 3 parallel workers (xdist)
   - Each worker: opens Chromium browser, creates isolated test instance
   - Each test: calls HTTP API to addon, then browser interactions

4. Each test creates unique instance:
   ```python
   instance_name = unique_name("scenario1")  # → "scenario1-w0-1"
   port = unique_port(3200)                   # → 3200 (worker 0)
   ```

5. Test workflow example (Scenario 1):
   ```python
   # 1. Browser: Click "Add Instance" button
   await page.click("button:has-text('Add Instance')")

   # 2. Browser: Fill form + create
   await page.fill("#newName", instance_name)
   await page.fill("#newPort", str(port))
   await page.click("#addInstanceModal button:has-text('Create Instance')")

   # 3. API: Verify instance running
   async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
       data = await resp.json()
       instance = next((i for i in data if i['name'] == instance_name))
       assert instance['running']  # Real Squid process confirmed
   ```

**Parallelization**

✅ **No Conflicts**
- Each worker gets 1000 ports (e.g., worker 0: 3200-4199, worker 1: 4200-5199)
- Each test gets unique instance name (e.g., "test-w0-1", "test-w1-2")
- Shared addon container (single :8099) handles all worker requests

✅ **Performance**
- 37 E2E tests execute in ~180 seconds with 3 workers
- Each Scenario test (1-7) takes ~25-40 seconds
- Edge case tests take ~5-10 seconds
- Overhead per test: ~0.5 seconds

**No Mocks Verification**

✅ Verified (grep search across tests/e2e/):
- NO `@patch` decorators
- NO `MagicMock` usage
- NO `monkeypatch` fixtures
- NO `Mock()` calls
- NO `AsyncMock` usage

All E2E tests are **100% real** (addon + Squid + browser).

### Running Tests

```bash
# All suites (Docker) - ~180 seconds
./run_tests.sh

# Specific suite
./run_tests.sh unit        # Unit + integration (~60 seconds)
./run_tests.sh e2e         # E2E only (~180 seconds)

# Parallel execution
pytest tests/ -n auto                  # Auto-detect workers
pytest tests/e2e/ -n 4                 # 4 parallel workers
pytest tests/unit/ -n auto -v          # Unit tests parallel

# Single test
pytest tests/unit/test_proxy_manager.py::test_create_instance -v
pytest tests/e2e/test_scenarios.py::test_scenario_1_setup_proxy_with_auth -n 1 -v

# Debug mode (serial execution)
pytest tests/e2e/ -n 1 -v --tb=short
```

### Parallelization Details

**Port Allocation**: Each xdist worker gets 1000 ports
- Worker 0: ports 3200-4199
- Worker 1: ports 4200-5199
- Worker N: ports (N×1000 + 3200) - (N×1000 + 4199)

**Instance Naming**: Format `{base}-w{worker_id}-{counter}` prevents conflicts
- Example: "proxy-w0-1", "proxy-w1-2", "proxy-w3-5"

**Browser Optimization**: Session-scoped browser (one per worker)
- Reduces startup overhead from ~3s per test to ~3s per worker
- Each test creates fresh page for isolation

**Performance**: ~100 tests in 14.5 seconds (4-6x speedup vs serial)

### Test Results

- **Unit Tests**: 40/40 passing ✅
- **Integration Tests**: 60/60 passing ✅
- **E2E Tests**: 37 passing ✅
- **Total**: 100+ tests, 100% success rate
- **Execution Time**: 14.5 seconds (parallel)

### Writing Tests

**Backend test template** (`tests/unit/test_feature.py`):

```python
import pytest
from proxy_manager import ProxyInstanceManager

@pytest.mark.unit
async def test_create_instance_basic(mock_popen, temp_data_dir):
    """Test creating a basic HTTP instance."""
    manager = ProxyInstanceManager(data_dir=temp_data_dir)

    result = await manager.create_instance(
        name='test',
        port=3128,
        https_enabled=False
    )

    assert result['name'] == 'test'
    assert result['port'] == 3128
    assert result['status'] == 'running'
```

**Frontend test template** (`squid_proxy_manager/frontend/src/features/instances/tests/InstanceList.test.tsx`):

```typescript
import { render, screen } from '@testing-library/react';
import { InstanceList } from '../InstanceList';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

describe('InstanceList', () => {
  it('renders empty state when no instances', () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <InstanceList />
      </QueryClientProvider>
    );

    expect(screen.getByText(/No instances/)).toBeInTheDocument();
  });
});
```

---

## IDE Setup

### VS Code / Cursor

**Install Extensions**:
- Python (ms-python.python)
- Black Formatter (ms-python.black-formatter)
- Ruff (charliermarsh.ruff)
- Playwright Test for VSCode (ms-playwright.playwright)
- TypeScript Vue Plugin (Vue) - for frontend

**.vscode/settings.json**:

```json
{
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit"
    }
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "[json]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  }
}
```

**Debug Frontend Tests**:
1. Set breakpoint in test file
2. Right-click → "Debug Test"
3. Playwright inspector opens automatically

### PyCharm

1. Settings → Tools → Python Integrated Tools: pytest
2. Settings → Tools → Black: Enable "On save"
3. Settings → Editor → Inspections: Enable Ruff

**Debug Backend Tests**:
1. Right-click test → "Run with Coverage"
2. Or use built-in debugger (Shift+F9)

---

## Common Issues & Debugging

### Tests Fail on First Run

**Cause**: Docker images not built
**Fix**:
```bash
./setup_dev.sh
./run_tests.sh unit
```

### "Port already in use" Error

**Cause**: Previous test didn't clean up
**Fix**:
```bash
docker compose -f docker-compose.test.yaml down -v
./run_tests.sh
```

### Squid Crashes with "FATAL: No valid signing certificate"

**Cause**: HTTPS config missing cert or `ssl_bump` directive
**Fix**:
1. Check `squid_proxy_manager/rootfs/app/squid_config.py`
2. Verify: `https_port` has cert/key paths, NO `ssl_bump`
3. Verify: cert file permissions 0o644
4. Test: `./run_tests.sh unit`

### Modal/Dialog Not Showing in UI

**Cause**: CSS visibility or conditional rendering
**Fix**:
```bash
# 1. Use Playwright MCP to inspect
npm run dev
# Inspect element → Check CSS (display, z-index, visibility)

# 2. Check React component
cat squid_proxy_manager/frontend/src/features/instances/AddInstanceModal.tsx

# 3. Verify conditional rendering
# {isOpen && <Modal />}  # or {showModal && ...}

# 4. Test
npm run test -- AddInstanceModal --watch
```

### API Returns 407 (Proxy Auth Required) in Tests

**Cause**: User not added or password wrong
**Fix**:
1. Check test adds user: `await manager.add_user('testuser', 'password')`
2. Check auth isolation: Each instance has unique passwd file
3. Run integration test: `./run_tests.sh unit`

### Form Validation Not Working

**Cause**: Missing validation logic or wrong event handler
**Fix**:
```bash
# 1. Check component: features/instances/AddInstanceForm.tsx
# - Does onChange update state?
# - Does validation function exist?
# - Is submit button conditioned on isFormValid?

# 2. Test:
npm run test -- AddInstanceForm --watch

# 3. Playwright inspection:
npm run dev
# Click form, type invalid value, check error message
```

### E2E Test Hangs or Times Out

**Cause**: Async operation not completing or selector not found
**Fix**:
```bash
# 1. Increase timeout (in test):
await page.waitForSelector('button:has-text("Create")', { timeout: 10000 });

# 2. Use Playwright MCP to debug:
# - Record test with Inspector
# - Check Network tab for pending requests
# - Use "Pause on exception" to catch errors

# 3. Check backend logs:
docker compose -f docker-compose.test.yaml logs addon

# 4. Reduce test scope:
./run_tests.sh unit  # Run backend first
```

---

## Commit Message & PR Standards

### Commit Message Format

**Convention**: `type(scope): subject`

```
type(scope): subject

optional body explaining why (not what)

optional footer referencing issues
```

**Types**:
- `feat`: New feature (relates to REQUIREMENTS.md FR)
- `fix`: Bug fix (relates to REQUIREMENTS.md Known Issue)
- `test`: Add/update test (relates to TEST_PLAN.md)
- `docs`: Documentation update (README, DEVELOPMENT.md, etc.)
- `refactor`: Code reorganization (no behavior change)
- `perf`: Performance improvement
- `chore`: Tooling, CI, non-code changes
- `security`: Security hardening

**Examples**:

```
# Feature with security impact
feat(auth): add user account locking after failed attempts

- Issue: Users can brute-force credentials
- Fix: Lock account for 15min after 5 failed attempts
- Tests: tests/unit/test_auth_manager.py::test_account_locking
- Docs: REQUIREMENTS.md FR-2

# Bug fix with root cause
fix(cert): cert permissions 0o600 prevents Squid reading

- Root Cause: Squid user (UID 101) needs read access to key file
- Fix: Changed from 0o600 to 0o644
- Tests: tests/integration/test_file_permissions.py
- Docs: REQUIREMENTS.md Known Issues section

# Test addition
test(https): add E2E test for HTTPS connectivity

- Scenario: Enable HTTPS, verify client can connect
- Tests: tests/e2e/test_https_ui.py::test_https_proxy_works
- Coverage: FR-3, HTTPS Support

# Documentation
docs: update DEVELOPMENT.md with security best practices

- Add: Security testing gates (bandit, trivy, trufflehog)
- Add: Code quality standards (>80% coverage)
- Add: PR checklist for code reviewers
```

### Pull Request Template

**Before creating PR, verify**:
- [ ] All tests passing: `./run_tests.sh` (exit code 0)
- [ ] Security checks: `bandit`, `trivy`, `trufflehog`
- [ ] Code quality: `black`, `ruff`, `npm run lint`
- [ ] Type checking: `mypy`, `npm run typecheck`
- [ ] Documentation updated: REQUIREMENTS.md, TEST_PLAN.md, README.md
- [ ] Commit messages follow format above

**PR Description Template**:

```markdown
## What
Brief description of change (1-2 sentences)

## Why
Problem this solves or requirement it fulfills
- Links REQUIREMENTS.md FR-X or Known Issue
- Explains design trade-offs if relevant

## How
Technical approach or algorithm used
- Backend: Which modules changed?
- Frontend: Which components changed?
- Database: Any schema changes?

## Tests
Test coverage added/modified
- Links TEST_PLAN.md section
- Lists new test files or functions
- Coverage: X% of new code

## Screenshots
If UI change: screenshots of before/after
- Use Playwright MCP: "Screenshot with Device" or "Compare"
- Include responsive views (mobile + desktop)

## Review Checklist
- [ ] Code review: Security, performance, maintainability
- [ ] Test review: Coverage >80%, all suites passing
- [ ] Documentation: Docs match implementation

## Breaking Changes
- [ ] No breaking API changes (or bump major version)
- [ ] No database migrations (or add migration script)
- [ ] No config changes (or add migration guide)
```

### Code Review Standards

**Reviewers must verify**:

✅ **Security** (must pass):
- No secrets in code (no API keys, passwords, tokens)
- No command injection vulnerabilities (validate/escape inputs)
- No privilege escalation (stays non-root)
- No hardcoded sensitive data

✅ **Quality** (must pass):
- Linting passes (black, ruff, prettier, eslint)
- Type checking passes (mypy, TypeScript strict)
- Tests pass (unit, integration, E2E)
- Coverage >80% of new code

✅ **Maintainability** (should pass):
- Code is readable and documented
- No TODOs without GitHub issues
- Follows project patterns (FR/NFR structure, test patterns)
- No unnecessary complexity

✅ **Performance** (should pass):
- No N+1 queries or inefficient algorithms
- No unintended sleeps or busy-waits
- File operations are bounded (not unbounded reads)

---

## Release Process

### Pre-Release Checklist

1. **Run all tests** (Docker-based):
   ```bash
   ./run_tests.sh
   echo "Exit code: $?"  # Must be 0
   ```

2. **Lint & type check** (Docker-based):
   ```bash
   # All tools run in Docker containers
   ./run_tests.sh              # Includes linting
   # Or manually:
   docker compose -f docker-compose.test.yaml --profile unit run --rm test-runner npm run lint
   ```

3. **Record workflows** (Docker-based - no local tools needed!):
   ```bash
   # Start addon locally
   ./run_addon_local.sh start

   # In another terminal, record workflows as GIFs using Docker
   docker compose -f docker-compose.test.yaml \
     --profile e2e \
     run --rm e2e-runner \
     python /app/record_workflows.py http://addon:8099

   # GIFs saved to docs/gifs/
   # See pre_release_scripts/README.md for details

   # Stop addon when done
   ./run_addon_local.sh stop
   ```

   **Why Docker?**
   - No local Playwright, ffmpeg, or Python needed
   - Consistent across all machines
   - Matches CI/CD environment
   - All tools pre-installed in e2e-runner image

4. **Update version** (3 places):
   ```bash
   # Edit these files and bump version to X.Y.Z:
   - squid_proxy_manager/config.yaml (version: "X.Y.Z")
   - squid_proxy_manager/Dockerfile (io.hass.version="X.Y.Z")
   - squid_proxy_manager/rootfs/app/main.py (if version string exists)
   ```

5. **Update docs**:
   - REQUIREMENTS.md: Add release entry if new features
   - TEST_PLAN.md: Add test notes if coverage changed
   - README.md: Update workflow GIFs from `docs/gifs/` (if new recordings made)
   - Commit: `docs: prepare release vX.Y.Z`

6. **Tag release**:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin main --tags
   ```

### Docker-First Principle

✅ **ALL development is containerized:**
- No local Python venv needed
- No local Playwright/ffmpeg installation
- All tools in Docker images
- Consistent across machines + CI

❌ **Never install locally:**
- Defeats containerization purpose
- Creates machine-specific issues
- Incompatible with CI/CD

### Post-Release

- Verify tag appears on GitHub
- Verify HA Add-ons index picks up new version
- Monitor issue tracker for regressions

---

## Setup Scripts Details

### setup_dev.sh (macOS / Linux)

```bash
#!/bin/bash
# Checks:
# ✓ Docker installed + version
# ✓ Docker Compose installed + version
# ✓ Node.js installed + npm (frontend only)
# ✓ Git installed
# Installation:
# ✓ npm install (frontend deps ONLY - no Python!)
# ✓ docker compose build (test containers with all Python tools)
```

### setup_dev.ps1 (Windows PowerShell)

```powershell
# Checks:
# ✓ Docker Desktop installed + running
# ✓ Docker Compose available
# ✓ Node.js installed + npm
# ✓ Git installed (or warn)
# Installation via:
# ✓ winget install (if needed)
# ✓ npm install (frontend deps)
# ✓ docker compose build (test containers)
```

---

## Quick Command Reference

```bash
# Setup & Testing
./setup_dev.sh              # Initial setup
./run_tests.sh              # All tests
./run_tests.sh unit         # Fast tests

# Frontend Development
npm run dev                 # Start dev server
npm run test                # Run frontend tests
npm run lint:fix            # Fix linting
npm run format              # Format code

# Backend Debugging
docker compose -f docker-compose.test.yaml logs addon
docker compose -f docker-compose.test.yaml exec addon bash

# Git Workflow
git checkout -b feature/name     # Create feature branch
git commit -m "feat: description"
git push origin feature/name     # Push & create PR
```

---

## Technical Reference

### System Components

**Web Server (`main.py`)**
- Framework: aiohttp (async)
- Port: 8099 (fixed, configured in config.yaml)
- UI: SPA embedded as Python string (HTML/CSS/JS inline)
- Ingress: Accessed via Home Assistant proxy

**Process Manager (`proxy_manager.py`)**
- Class: `ProxyInstanceManager`
- Process Model: `subprocess.Popen` with `-N` (no daemon)
- State: `instance.json` per instance + in-memory `processes` dict
- Lifecycle: create → start → stop → remove

**Config Generator (`squid_config.py`)**
- Class: `SquidConfigGenerator`
- Output: `/data/squid_proxy_manager/<name>/squid.conf`
- HTTPS: Uses `https_port` with `tls-cert`/`tls-key` (NO ssl_bump!)

**Certificate Manager (`cert_manager.py`)**
- Library: `cryptography`
- Type: Self-signed server certificate (NOT CA)
- Files: `server.crt`, `server.key` in instance directory
- Permissions: `0o644` for both (squid needs read access)

**Auth Manager (`auth_manager.py`)**
- Format: htpasswd (MD5-crypt / APR1)
- File: `/data/squid_proxy_manager/<name>/passwd`
- Squid Helper: `/usr/lib/squid/basic_ncsa_auth`

### API Endpoints

| Method | Endpoint | Action |
|--------|----------|--------|
| GET | `/api/instances` | List all instances |
| POST | `/api/instances` | Create instance |
| DELETE | `/api/instances/<name>` | Remove instance |
| POST | `/api/instances/<name>/start` | Start instance |
| POST | `/api/instances/<name>/stop` | Stop instance |
| POST | `/api/instances/<name>/restart` | Restart instance |
| PUT | `/api/instances/<name>/settings` | Update settings |
| GET | `/api/instances/<name>/users` | List users |
| POST | `/api/instances/<name>/users` | Add user |
| DELETE | `/api/instances/<name>/users/<user>` | Remove user |
| GET | `/api/instances/<name>/logs` | Get logs |
| POST | `/api/instances/<name>/test` | Test connectivity |

### Squid Configuration

**HTTP Instance**
```
http_port [::]:3128
cache_dir ufs /data/.../cache 100 16 256
access_log /data/.../access.log
cache_log /data/.../cache.log
auth_param basic program /usr/lib/squid/basic_ncsa_auth /data/.../passwd
auth_param basic realm Squid Proxy
acl authenticated proxy_auth REQUIRED
http_access allow authenticated
http_access deny all
```

**HTTPS Instance (CRITICAL: no ssl_bump!)**
```
https_port [::]:3129 tls-cert=/data/.../server.crt tls-key=/data/.../server.key
# NOTE: NO ssl_bump directive - it requires CA signing cert!
```

### Test Infrastructure

**Unit Tests (`tests/unit/`)**
- Mock filesystem, no real processes
- Test config generation, auth logic, cert generation
- Key: `test_squid_config_https.py` - verifies NO ssl_bump

**Integration Tests (`tests/integration/`)**
- Uses `fake_squid` script (shell script that accepts args)
- Tests API endpoints with mocked manager
- Network tests skipped in sandbox (use `@pytest.mark.network`)

**E2E Tests (`tests/e2e/`)**
- Real Squid: Docker container with actual squid binary
- Browser: Playwright (Chromium)
- Compose: `docker-compose.test.yaml`
- Key: `test_https_ui.py` - verifies HTTPS instance stays running

### Common Pitfalls

1. **ssl_bump**: Even `ssl_bump none all` requires a signing CA cert. Don't use it.
2. **window.confirm()**: Blocked in HA ingress iframe. Use custom modal.
3. **File permissions**: Squid runs as `squid` user, needs read access to certs.
4. **Port conflicts**: Each instance needs unique port in 3128-3140 range.
5. **Path quoting**: Squid 5.9 doesn't like quoted paths in `tls-cert=`/`tls-key=`.

### Debugging

**Check Squid Logs**
```bash
# In container
cat /data/squid_proxy_manager/logs/<name>/cache.log
```

**Common Errors**
| Error | Cause | Fix |
|-------|-------|-----|
| `FATAL: No valid signing certificate` | ssl_bump in config | Remove ssl_bump directive |
| `407 Proxy Authentication Required` | Wrong user/pass or passwd file | Check passwd path, verify user exists |
| `curl: (60) SSL certificate problem` | Self-signed cert | Use `curl --proxy-insecure` |

---

## Document Cross-Reference

- **[REQUIREMENTS.md](REQUIREMENTS.md)**: What to build (FRs, scenarios, known issues)
- **[TEST_PLAN.md](TEST_PLAN.md)**: How to test (test procedures, edge cases, CI gates)
- **[DESIGN_GUIDELINES.md](DESIGN_GUIDELINES.md)**: UI design patterns, components, styling
- **[README.md](README.md)**: User guide (how to use the add-on)

---

## Getting Help

1. **Check REQUIREMENTS.md Known Issues** for similar problems
2. **Search TEST_PLAN.md** for test reference to issue
3. **Check logs**: `docker compose logs addon`
4. **Use Playwright MCP** for UI issues
5. **File issue** with reproduction steps (use template in "Reporting Bugs")
