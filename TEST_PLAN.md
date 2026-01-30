# Unified Test & Fix Plan: HA Squid Proxy Manager

This document is the single source of truth for testing, validation, and fix workflows.
All previous plans are consolidated here.

## Goals
- All tests run in Docker with the **real Squid binary** (no fakes/mocks).
- E2E is mandatory for release.
- Fix real behavior, not just tests.
- Lint and security checks must pass without skipping.

## Environments
- **Local/CI**: Docker only (docker-compose / run_tests.sh)
- **Squid user**: must have write access to logs/cache (permissions are part of the tests)
- **Network**: E2E requires open loopback networking inside Docker

## Test Suites

### 1) Unit
Focus: pure logic and config generation.
- `tests/unit/test_squid_config.py`
- `tests/unit/test_cert_manager.py`
- `tests/unit/test_auth_manager.py`

Key checks:
- Config generation uses correct data paths and permissions.
- HTTPS config uses `https_port` with `tls-cert`/`tls-key` **and no `ssl_bump`**.
- Certificates are **server certs** (not CA), valid PEM, and correct permissions.

### 2) Integration (real Squid)
Focus: aiohttp handlers, filesystem, process lifecycle, and config correctness.
- API handlers for create/update/delete.
- Squid startup/log patterns (real Squid format).
- HTTPS certificate creation and readability by Squid.

Key checks:
- Temp dirs are world-writable for Squid user.
- Config paths are absolute and readable.
- Instances start/stop cleanly and logs are created.

### 3) Frontend (React SPA)
Focus: UI primitives, API client, and form validation.
- `squid_proxy_manager/frontend/src/tests/button.test.tsx`
- `squid_proxy_manager/frontend/src/tests/apiClient.test.ts`
- `squid_proxy_manager/frontend/src/tests/validation.test.ts`

Key checks:
- API client resolves ingress base paths correctly.
- Form validation requires HTTPS cert params when enabled.
- UI primitives render and handle loading state.

### 4) E2E (UI + functional)
Focus: full flow in Docker with the add-on running.
- UI flows: create instance, manage users, logs, settings, delete.
- Proxy flow: HTTP + HTTPS with auth.

Key checks:
- Instance lifecycle works end-to-end.
- HTTPS enablement works from UI and stays running.
- Proxy connectivity works with credentials.
- HTTPS proxy connectivity via **Test** modal returns success for HTTPS instances.
- Add-user and delete-instance operations show progress and keep UI responsive.

UI E2E cases to cover:
- Test modal on HTTPS instance returns success and shows HTTP code.
- Add-user shows progress/disabled inputs while request is running.
- Delete-instance shows progress/disabled buttons until completion.

## HTTPS Coverage (Critical)
- No `ssl_bump` in config for HTTPS-only proxy.
- Certs are server certs with `ExtendedKeyUsage=SERVER_AUTH`.
- Cert/key permissions are readable by Squid.
- Squid starts successfully with HTTPS enabled.
- HTTPS proxy requests succeed (CONNECT via HTTPS proxy).

## CI / Release Gates
- **Lint**: `pre-commit run --all-files` in Docker (no skips)
- **Security**: bandit (Docker)
- **Unit + Integration**: Docker test runner
- **E2E**: Docker (addon + e2e runner)

Release is blocked unless **all gates pass**.

## How to Run
```bash
# Lint (Docker)
docker compose -f docker-compose.test.yaml --profile lint up --build --exit-code-from lint-runner

# Security (Docker)
docker compose -f docker-compose.test.yaml --profile security up --build --exit-code-from security-runner

# Unit + Integration
docker compose -f docker-compose.test.yaml --profile unit up --build --exit-code-from test-runner

# E2E
BUILD_ARCH=amd64 docker compose -f docker-compose.test.yaml --profile e2e up --build --exit-code-from e2e-runner
```

## Fix Workflow (When CI Fails)
1) **Reproduce in Docker** (same command as CI).
2) **Identify root cause** (logs, exit codes, failing assertion).
3) **Fix functionality** (not the test).
4) **Add/adjust tests** only if behavior or coverage is incorrect.
5) **Re-run the same Docker command** until green.

## Release Checklist
- All CI gates are green.
- Version bumped in:
  - `squid_proxy_manager/config.yaml`
  - `squid_proxy_manager/Dockerfile` (io.hass.version)
  - `squid_proxy_manager/rootfs/app/main.py`
- Tag and push release.
