# Copilot Instructions: HA Squid Proxy Manager

## Project Overview

**HA Squid Proxy Manager** is a Home Assistant Add-on (not a custom component) that manages multiple Squid proxy instances in Docker with independent configurations, users, and optional HTTPS support.

- **Type**: Home Assistant Add-on (runs in container)
- **Language**: Python 3 (aiohttp)
- **Testing**: Docker-based (unit + integration + e2e)
- **Deployment**: YAML add-on to Home Assistant Supervisor

## Engineering Principles (Read First)

### Documentation Management

⚠️ **Single Source of Truth for All Knowledge**

- **NO new architecture documents** - All knowledge accumulates in 4 primary files:
  - [DEVELOPMENT.md](../DEVELOPMENT.md) - How to build, test, develop (processes & workflows)
  - [REQUIREMENTS.md](../REQUIREMENTS.md) - What and why (user scenarios, requirements, quality standards)
  - [TEST_PLAN.md](../TEST_PLAN.md) - What to test (test scenarios, coverage, results)
  - [DESIGN_GUIDELINES.md](../DESIGN_GUIDELINES.md) - UI/frontend design patterns, component architecture, styling standards

- **When adding new features or fixing bugs:**
  - Update the appropriate primary file (DEVELOPMENT, REQUIREMENTS, TEST_PLAN, or DESIGN_GUIDELINES)
  - Do NOT create new `.md` files (no FEATURE_PLAN.md, BUGFIX_SUMMARY.md, etc.)
  - Do NOT create numbered versions (no HTTPS_FIX_1.1.18_SUMMARY.md)
  - Archive or delete superseded documentation to maintain single source of truth

- **What goes where:**
  - DEVELOPMENT.md: Architecture diagrams, setup steps, testing architecture, IDE setup, debugging
  - REQUIREMENTS.md: User scenarios, acceptance criteria, non-functional requirements, known issues
  - TEST_PLAN.md: Test scenarios, coverage by feature, how to run tests, test results
  - DESIGN_GUIDELINES.md: UI components, design patterns, styling, frontend architecture
  - `.github/copilot-instructions.md`: Engineering principles, Docker-first policies, critical bug patterns
  - `pre_release_scripts/README.md`: How to run release workflows (recording GIFs, etc.)
  - **NO separate docs files**: All knowledge in the 4 primary files + these meta-files above

### Core Engineering Principles

1) **Docker-first development and testing (STRICTLY ENFORCED)**
   - ✅ ALL development runs in Docker containers
   - ❌ NEVER install tools locally (Playwright, ffmpeg, Python packages, etc.)
   - Dev and CI use identical Docker containers for consistency
   - Prefer `run_tests.sh` and docker-compose workflows over local command execution
   - If a tool is needed, add it to a Dockerfile, rebuild image, run in container

2) **E2E is mandatory for release**
   - All unit, integration, and E2E tests must pass before any release.
   - E2E failures block feature completion.

3) **Fix behavior, not just tests**
   - When a test fails, fix the underlying functionality, not the test itself.

4) **Linter findings: fix, don’t suppress**
   - Suppress only if there is no safe/clean alternative and document why.
   - Code quality and security checks are first-class requirements.

5) **No skipped checks in pre-commit or CI**
   - Do not skip lint/security hooks. Fix the underlying issues instead.
   - CI may split lint and security into separate jobs, but both must pass.

6) **Actions failures require root-cause fixes**
   - Do not weaken CI (no skipping, no lowering thresholds).
   - Always align CI with Docker-based workflows for dev/prod parity.

7) **No evasive renames to pass checks**
   - Do not rename variables or restructure code just to satisfy tools/tests.
   - Fix the root cause or update baselines with a clear rationale.

8) **Terminal commands: No timeouts or waits**
   - ❌ NEVER use `timeout` command on terminal calls (e.g., `timeout 120 docker compose ...`)
   - ❌ NEVER add sleep/wait pauses (e.g., `sleep 5` before running commands)
   - ✅ Let processes complete naturally or fail cleanly
   - ✅ If a command hangs, investigate root cause instead of adding timeouts
   - ✅ Use health checks in docker-compose instead of waits for readiness
   - Rationale: Timeouts mask underlying issues and are unreliable across different machines/CI environments

9) **All tests MUST have timeouts (CRITICAL)**
   - ⚠️ **MANDATORY**: Every test must have a timeout to prevent hanging forever in CI
   - ✅ Global timeout configured in `pytest.ini`: `timeout = 180` (3 minutes for E2E tests)
   - ✅ `pytest-timeout` plugin MUST be installed in all test Docker images
   - ✅ Tests should fail fast if they hang or block on user actions
   - ❌ NEVER let tests run indefinitely - this wastes CI resources and blocks other jobs
   - **Root Cause**: Without `pytest-timeout`, tests can hang forever (e.g., 9+ minutes before manual cancellation)
   - **Example of hanging test**: Test stuck polling API every 10s with no progression
   - **Fix**: Ensure `pytest-timeout` is in Dockerfile and timeout values are appropriate
   - Rationale: Fast feedback on stuck tests, better CI resource utilization, prevent manual intervention

## Docker Image Architecture

**Strict separation: Production vs Test images**

```
PRODUCTION IMAGES
├─ addon (squid_proxy_manager/Dockerfile)
│  ├─ Base: homeassistant/base (alpine)
│  ├─ Size: ~150MB (minimal, lean)
│  ├─ Contains: main.py, proxy_manager.py, squid binary
│  ├─ NO test tools, dev dependencies, or Playwright
│  ├─ Security: Non-root (UID 1000:1000), read-only fs
│  └─ ✅ Production-ready only

TEST IMAGES
├─ test-runner (tests/Dockerfile.test)
│  ├─ Base: python:3.11-slim
│  ├─ Size: ~400MB (minimal)
│  ├─ Contains: pytest, squid, unit/integration test dependencies
│  ├─ NO Playwright, ffmpeg, or E2E tools
│  ├─ Purpose: Unit + integration tests
│  └─ ✓ Docker-only execution

├─ e2e-runner (tests/Dockerfile.e2e) ← Recording workflows use this
│  ├─ Base: python:3.11-slim
│  ├─ Size: ~450MB (minimal)
│  ├─ Contains: Playwright, ffmpeg, pytest, E2E tests
│  ├─ NO Squid, pytest-xdist heavy packages, build tools
│  ├─ Purpose: Browser automation, E2E tests, GIF recording
│  └─ ✓ Docker-only execution

├─ lint-runner (tests/Dockerfile.lint)
│  ├─ Purpose: black, ruff, pre-commit checks
│  └─ ✓ Separate specialized image

├─ security-runner (tests/Dockerfile.security)
│  ├─ Purpose: bandit, security scanning
│  └─ ✓ Separate specialized image

└─ ui-runner (tests/Dockerfile.frontend)
   ├─ Purpose: Frontend linting, type checking, tests
   └─ ✓ Separate specialized image
```

**Key principle**: Each image purpose-built, minimal dependencies

## Architecture at a Glance

```
┌─────────────────────────────────────────────┐
│ PRODUCTION: addon (alpine base)             │
├─────────────────────────────────────────────┤
│ main.py (aiohttp server :8099)              │
│  ├─ REST API: /api/instances/*              │
│  └─ SPA UI: embedded HTML/JS/CSS            │
├─────────────────────────────────────────────┤
│ manager.py → subprocess.Popen spawns Squid  │
│  ├─ squid -N -f config :3128 (instance 1)   │
│  ├─ squid -N -f config :3129 (instance 2)   │
│  └─ ... (N instances)                       │
├─────────────────────────────────────────────┤
│ Supporting modules:                         │
│  ├─ squid_config.py: Generate Squid conf    │
│  ├─ auth_manager.py: Manage htpasswd        │
│  └─ cert_manager.py: Generate self-signed   │
└─────────────────────────────────────────────┘

     ↓ (for tests)

┌─────────────────────────────────────────────┐
│ TEST: e2e-runner (for workflows)            │
├─────────────────────────────────────────────┤
│ Browser automation (Playwright)             │
│ GIF recording (ffmpeg)                      │
│ E2E test execution (pytest)                 │
└─────────────────────────────────────────────┘
```

## Core Components

| File | Purpose | Key Classes/Functions |
|------|---------|-----|
| [squid_proxy_manager/rootfs/app/main.py](squid_proxy_manager/rootfs/app/main.py) | aiohttp API server + SPA UI | `create_instance()`, `remove_instance()` handlers |
| [squid_proxy_manager/rootfs/app/proxy_manager.py](squid_proxy_manager/rootfs/app/proxy_manager.py) | Process lifecycle management | `ProxyInstanceManager.start/stop/remove_instance()` |
| [squid_proxy_manager/rootfs/app/squid_config.py](squid_proxy_manager/rootfs/app/squid_config.py) | Squid config generation | `SquidConfigGenerator.generate_config()` |
| [squid_proxy_manager/rootfs/app/auth_manager.py](squid_proxy_manager/rootfs/app/auth_manager.py) | htpasswd-based auth | `AuthManager.add_user()`, `verify_password()` |
| [squid_proxy_manager/rootfs/app/cert_manager.py](squid_proxy_manager/rootfs/app/cert_manager.py) | Self-signed certificates | `CertificateManager.generate_certificate()` |

## Data Storage Paths (CRITICAL)

```
/data/squid_proxy_manager/
├── <instance-name>/                    # Per-instance directory
│   ├── squid.conf                      # Generated config file
│   ├── passwd                          # htpasswd file (UNIQUE per instance!)
│   ├── instance.json                   # Metadata
│   ├── server.crt                      # HTTPS cert (if enabled)
│   └── server.key                      # HTTPS key (if enabled)
├── certs/                              # Legacy/backup cert location
│   └── <instance-name>/
│       ├── squid.crt                   # Alternative cert path
│       └── squid.key                   # Alternative key path
└── logs/
    └── <instance-name>/
        ├── access.log                  # Squid proxy access logs
        ├── cache.log                   # Squid cache diagnostics
        └── cache/                      # Squid cache storage
```

## Critical Bug Patterns (MUST AVOID)

### 1. SSL/TLS Configuration for HTTPS

❌ **WRONG** - Causes `FATAL: No valid signing certificate` error:
```python
# DO NOT include ssl_bump - it requires signing CA cert even with "none all"
```
config_lines.append("ssl_bump none all")  # DELETE THIS LINE
```

✅ **CORRECT** - Simple HTTPS proxy (no certificate interception):
```python
cert_file = f"{instance_cert_dir}/squid.crt"
key_file = f"{instance_cert_dir}/squid.key"
https_line = f"https_port {port} tls-cert={cert_file} tls-key={key_file}"
config_lines.append(https_line)
# NO ssl_bump directive!
```

**Why**: `ssl_bump` enables dynamic HTTPS interception, requiring a CA signing certificate. For a simple HTTPS proxy (just encrypted client-to-proxy connection), omit it.

### 2. Window Dialogs Blocked in Home Assistant Iframe

❌ **WRONG** - `window.confirm()` is blocked in HA ingress:
```javascript
if (window.confirm('Delete?')) { deleteInstance(name); }
```

✅ **CORRECT** - Use custom HTML modal:
```javascript
function deleteInstance(name) {
    document.getElementById('deleteModal').style.display = 'block';
    document.getElementById('deleteMessage').textContent = `Delete "${name}"?`;
    document.getElementById('confirmDeleteBtn').onclick = () => confirmDelete(name);
}
```

### 3. Instance-Specific Auth Files

❌ **WRONG** - All instances sharing one passwd file:
```python
auth_path = "/data/squid_proxy_manager/passwd"  # Shared!
```

✅ **CORRECT** - Each instance has unique passwd file:
```python
auth_path = f"/data/squid_proxy_manager/{instance_name}/passwd"  # Isolated!
```

**Why**: Each instance is independent; shared auth breaks isolation.

## Code Patterns

### Process Management (proxy_manager.py)

Process spawning uses `subprocess.Popen` with `-N` (no daemon mode):

```python
process = subprocess.Popen(
    [SQUID_BINARY, "-N", "-f", str(config_file)],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
self.processes[name] = process
```

**Key points**:
- `-N` prevents daemonization (process stays attached for lifecycle tracking)
- Config file path MUST use `-f` flag (not stdin)
- Processes dict stores active instances for start/stop/remove
- Cleanup on instance removal: kill process + delete instance directory

### Async API Patterns (main.py)

aiohttp handlers are async functions returning JSON responses:

```python
async def handle_create_instance(request):
    """POST /api/instances"""
    data = await request.json()
    result = await manager.create_instance(
        name=data['name'],
        port=data['port'],
        https_enabled=data.get('https_enabled', False),
        users=data.get('users', [])
    )
    return web.json_response(result)
```

**Key patterns**:
- All manager calls are `await` (even though many aren't actually async internally)
- Request/response as JSON via `request.json()` / `web.json_response()`
- Error handling wraps try/catch around manager calls
- Path normalization middleware handles HA ingress double-slash paths

### Configuration Generation (squid_config.py)

Generate config as list of lines, then join and write:

```python
config_lines = [
    f"# Comment for {instance_name}",
    "pid_filename none",  # Prevent PID file conflicts
    f"https_port {port} tls-cert={cert_file} tls-key={key_file}",
    "auth_param basic program /usr/lib/squid/basic_ncsa_auth /path/to/passwd",
    "http_access allow authenticated",
    "http_access deny all",
]
config_content = "\n".join(config_lines)
config_file.write_text(config_content, encoding="utf-8")
config_file.chmod(0o644)  # Squid needs read access
```

**Critical settings**:
- `pid_filename none` - Prevents conflicts when multiple instances exist
- `cache deny all` - Disables caching (proxy-only mode)
- `auth_param basic realm` - Sets realm displayed to users
- File permissions `0o644` - Squid (non-root) must read config and passwd

### Authentication (auth_manager.py)

Uses htpasswd MD5-crypt format (compatible with Squid):

```python
# Add user (generates hashed password)
auth_manager.add_user(username, password)  # Uses htpasswd command

# Squid config references:
f"auth_param basic program /usr/lib/squid/basic_ncsa_auth {passwd_file}"

# Verify password locally (for testing):
auth_manager.verify_password(username, password_attempt)
```

**Key points**:
- Passwords hashed with `htpasswd -bc` (MD5-crypt/APR1)
- File format: `username:$apr1$...hashed...`
- Squid uses `/usr/lib/squid/basic_ncsa_auth` helper to validate
- Each instance has isolated passwd file

### Certificate Generation (cert_manager.py)

Self-signed server certificate (not CA):

```python
cert_manager.generate_certificate(
    cert_path="/data/.../server.crt",
    key_path="/data/.../server.key",
)
```

**Key points**:
- Generates 365-day self-signed cert
- Uses `cryptography` library (not OpenSSL command-line)
- Certificate is for server identity only (not interception)
- File permissions `0o644` so Squid can read

## Testing Workflow

### Run All Tests (Recommended)
```bash
./run_tests.sh          # ALL tests in Docker (unit + integration + e2e)
./run_tests.sh unit     # Unit + integration only (~1 min, faster)
./run_tests.sh e2e      # E2E only with real addon (~3 min)
```

### Test Architecture

| Suite | Container | Squid | Browser | Marker |
|-------|-----------|-------|---------|--------|
| Unit | test-runner | Mocked | None | `@pytest.mark.unit` |
| Integration | test-runner | Real | None | `@pytest.mark.integration` |
| E2E | e2e-runner + addon | Real addon | Playwright | `@pytest.mark.e2e` |

**Key test files**:
- [tests/unit/test_squid_config_https.py](tests/unit/test_squid_config_https.py) - Verifies NO ssl_bump in HTTPS config
- [tests/unit/test_proxy_manager.py](tests/unit/test_proxy_manager.py) - Process lifecycle (mocked Popen)
- [tests/integration/test_e2e_flows.py](tests/integration/test_e2e_flows.py) - Real Squid container tests
- [tests/e2e/test_https_ui.py](tests/e2e/test_https_ui.py) - Browser-based UI tests with Playwright

### Test Patterns

Unit tests mock `subprocess.Popen`:
```python
@patch('subprocess.Popen')
async def test_create_instance_basic(mock_popen, temp_data_dir):
    mock_popen.return_value = MagicMock()
    manager = ProxyInstanceManager()
    result = await manager.create_instance('test', 3128)
    assert result['name'] == 'test'
```

Integration tests use real Squid:
```python
@pytest.mark.integration
async def test_instance_can_authenticate(real_squid_instance):
    # Uses actual Squid container to test auth flow
    response = await http_client.get(
        'http://127.0.0.1:3128',
        proxy_auth=('user', 'pass')
    )
```

## Development Environment

**Only Docker required** - no Python venv, no local dependencies.

```bash
./setup_dev.sh          # One-time setup (builds containers)
./run_tests.sh          # Run tests in Docker
```

### IDE Setup (Optional)
Install Python extensions for linting/formatting:
- **Python** (ms-python.python)
- **Black Formatter** (autopep8, black)
- **Ruff** (fast linting)

No local Python interpreter needed - linters run in containers.

## Release Checklist

When bumping version to X.Y.Z:

1. `squid_proxy_manager/config.yaml` → `version: "X.Y.Z"`
2. `squid_proxy_manager/Dockerfile` → `io.hass.version="X.Y.Z"`
3. `squid_proxy_manager/rootfs/app/main.py` → Update UI version string (if visible)
4. Run full test suite: `./run_tests.sh`
5. Tag release: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
6. Push: `git push origin main --tags`

## Common Debugging

### Squid crashes immediately
→ Check `cache.log` for config errors: `cat /data/squid_proxy_manager/logs/<name>/cache.log`
→ Verify config syntax: `squid -k parse -f /path/to/squid.conf`

### Authentication fails (407 Proxy Auth Required)
→ Verify passwd file exists: `ls -la /data/squid_proxy_manager/<name>/passwd`
→ Verify user in passwd file: `grep username /data/squid_proxy_manager/<name>/passwd`
→ Squid helper path must exist: `/usr/lib/squid/basic_ncsa_auth`

### HTTPS certificate error (SSL_ERROR_* in browser)
→ Self-signed certs are expected - use `curl --proxy-insecure`
→ Verify cert file readable by squid user: `ls -la /data/squid_proxy_manager/<name>/server.crt`

### Port already in use
→ Each instance must have unique port (typically 3128-3140)
→ Check running processes: `ps aux | grep squid`

## File Organization Reference

```
squid_proxy_manager/
├── rootfs/app/              # Main Python application
├── Dockerfile               # Container image definition
├── config.yaml              # HA addon metadata
└── README.md

tests/
├── unit/                    # Fast unit tests (no dependencies)
├── integration/             # Real Squid container tests
└── e2e/                     # Browser tests with real addon

.github/
└── copilot-instructions.md  # This file
```

## External Dependencies

- **aiohttp**: Async web server
- **cryptography**: Certificate generation
- **passlib**: Password hashing (htpasswd format)
- **Squid 5.9**: Proxy binary in Docker image

## Integration Points

1. **Home Assistant Supervisor**: Via `http://supervisor` with `SUPERVISOR_TOKEN`
2. **Ingress**: Accessible via HA proxy (handles path rewriting)
3. **Configuration**: Loaded from `/data/options.json` at startup
4. **Persistent Storage**: `/data/` mount shared with HA
