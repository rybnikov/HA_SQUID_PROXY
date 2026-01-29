# Squid Proxy Manager - Requirements & Work Log

## Project Overview

Home Assistant Add-on that manages multiple Squid proxy instances with HTTPS support and basic authentication.

## Functional Requirements

### FR-1: Proxy Instance Management
- **FR-1.1**: Create new proxy instances with name, port, HTTPS option
- **FR-1.2**: Start/Stop proxy instances
- **FR-1.3**: Delete proxy instances (with cleanup of config, logs, certificates)
- **FR-1.4**: List all proxy instances with status
- **FR-1.5**: Update instance settings (port, HTTPS)

### FR-2: User Authentication
- **FR-2.1**: Add users to proxy instances (username/password)
- **FR-2.2**: Remove users from proxy instances
- **FR-2.3**: User isolation between instances (each instance has own passwd file)
- **FR-2.4**: Support multiple users per instance
- **FR-2.5**: Password hashing using MD5-crypt (APR1) for Squid compatibility

### FR-3: HTTPS Support
- **FR-3.1**: Enable HTTPS on proxy instances
- **FR-3.2**: Generate self-signed server certificates
- **FR-3.3**: Certificate parameters customization (CN, validity, key size, country, org)
- **FR-3.4**: Regenerate certificates on demand
- **FR-3.5**: Certificate validation before Squid starts
- **FR-3.6**: Certificate file permissions for Squid access (0o644)
- **FR-3.7**: HTTPS proxy connectivity works end-to-end (CONNECT via HTTPS proxy returns 200 with valid credentials)

### FR-4: Web UI
- **FR-4.1**: Dashboard showing all instances and status
- **FR-4.2**: Add Instance modal with HTTPS and certificate settings
- **FR-4.3**: Settings modal for instance configuration
- **FR-4.4**: User management modal
- **FR-4.5**: Log viewer for access and cache logs
- **FR-4.6**: Test connectivity button
- **FR-4.7**: Progress indicators for async operations
- **FR-4.8**: Add-user operation shows progress and disables inputs while running
- **FR-4.9**: Delete instance operation shows progress and disables actions while running

### FR-5: API Endpoints
- **FR-5.1**: GET /api/instances - List all instances
- **FR-5.2**: POST /api/instances - Create new instance
- **FR-5.3**: DELETE /api/instances/{name} - Delete instance
- **FR-5.4**: POST /api/instances/{name}/start - Start instance
- **FR-5.5**: POST /api/instances/{name}/stop - Stop instance
- **FR-5.6**: PATCH /api/instances/{name} - Update instance settings
- **FR-5.7**: POST /api/instances/{name}/users - Add user
- **FR-5.8**: DELETE /api/instances/{name}/users/{username} - Remove user
- **FR-5.9**: POST /api/instances/{name}/certs - Regenerate certificates
- **FR-5.10**: POST /api/instances/{name}/test - Test connectivity

## Non-Functional Requirements

### NFR-1: Security
- Passwords stored as hashes (MD5-crypt)
- Certificate key files accessible only to Squid process
- No secrets in logs

### NFR-2: Performance
- Async operations for certificate generation
- Non-blocking UI during long operations
- Async/long-running UI actions (add user, delete instance) show progress and keep UI responsive

### NFR-3: Reliability
- Certificate validation before Squid starts
- Graceful error handling with clear messages
- Process cleanup on instance deletion

### NFR-4: Compatibility
- Home Assistant Add-on format
- Squid 5.9 on Alpine Linux
- Ingress support

## Bug Fixes & Issues Log

### v1.1.14 - User Management Bugs
- [x] Adding users via UI not working (407 auth error)
- [x] Cannot add more than one user
- [x] Users shared between instances (should be isolated)
- [x] Cannot remove proxy
- [x] Test button not working
- [x] Stop button not working

### v1.1.15 - Marketplace Detection
- [x] Updates not picked by marketplace (missing `url` field)

### v1.1.16 - HTTPS Certificate Permissions
- [x] HTTPS enable from UI failing
- [x] Certificate file wrong permissions (was 0o755, fixed to 0o644)

### v1.1.17 - HTTPS Certificate Type
- [x] HTTPS still failing (certificate was CA type, not server type)
- [x] Changed BasicConstraints ca=True to ca=False
- [x] Added ExtendedKeyUsage with SERVER_AUTH

### v1.1.18 - HTTPS Key File Permissions & UI Styling
- [x] HTTPS still failing (key file 0o600 not readable by Squid)
- [x] Changed key file permissions to 0o644
- [x] Added OpenSSL certificate validation
- [x] Fixed UI modal styling (dark theme, width)
- [x] Delete proxy not working from UI (fixed - added 404 check for missing instances)

## Test Requirements

### TR-1: Unit Tests
- [x] Certificate generation (server type, parameters)
- [x] Squid config generation (HTTP and HTTPS)
- [x] Auth manager (user add/remove, password hashing)
- [x] File permissions verification

### TR-2: Integration Tests
- [x] API endpoint testing
- [x] Instance lifecycle (create, start, stop, remove)
- [x] User management API
- [x] HTTPS certificate generation and validation
- [ ] HTTPS proxy functionality with real Squid (CONNECT over HTTPS proxy)

### TR-3: E2E Tests (UI)
- [x] Instance creation via UI
- [x] User management via UI
- [x] **Delete proxy via UI** (FIXED - added 404 check)
- [x] **HTTPS enable via UI** (COMPREHENSIVE TESTS ADDED)
- [x] Start/Stop buttons
- [x] Test connectivity button
- [x] Certificate settings UI
- [ ] **HTTPS proxy test via UI** (Test modal with HTTPS instance returns success)
- [ ] **Async UI feedback** for add-user and delete-instance operations

### TR-4: HTTPS Test Plan
- [x] Create HTTPS instance via UI (E2E test)
- [x] Verify certificate generation (Unit + Integration tests)
- [x] Verify certificate is server type (not CA) (Unit test)
- [x] Verify certificate file permissions (Unit + Integration tests)
- [x] Verify Squid can read certificates (Integration test)
- [ ] **Verify Squid starts successfully** (NEEDS PRODUCTION TESTING)
- [ ] **Verify proxy works with HTTPS** (NEEDS PRODUCTION TESTING)
- [x] Test certificate regeneration (E2E test)
- [x] Test certificate parameters (Unit test)
- [x] Test enable HTTPS on existing HTTP instance (E2E test)

### TR-5: Pre-commit & CI
- [x] Run all unit tests on commit (added to .pre-commit-config.yaml)
- [x] Run integration tests on commit (added to .pre-commit-config.yaml)
- [x] Fail commit if tests fail (pre-commit hook fails on test failure)
- [x] Include test run in release process (documented in release checklist)

## Release Checklist

### Before Each Release
1. [ ] Run full test suite: `./run_tests.sh`
2. [ ] All tests pass (106+ passed)
3. [ ] Bump version in:
   - [ ] `config.yaml`
   - [ ] `Dockerfile`
   - [ ] `main.py` (2 places)
4. [ ] Update CHANGELOG
5. [ ] Create git tag
6. [ ] Push to repository

## Architecture Decisions

### AD-1: Process-based Squid Management
Each proxy instance runs as a separate Squid process via `subprocess.Popen`.

### AD-2: Certificate File Permissions
Key files use 0o644 (world-readable) instead of 0o600 because Squid runs as a different user (nobody/squid) in the container.

### AD-3: MD5-crypt Password Hashing
Using `openssl passwd -apr1` for password hashing, compatible with Squid's `basic_ncsa_auth`.

### AD-4: Single Page Application
Web UI is embedded in `main.py` as an SPA to simplify deployment.

## Development Setup

```bash
# Install dependencies
./setup_dev.sh

# Run tests
./run_tests.sh

# Run specific tests
./run_tests.sh tests/unit/ -v
./run_tests.sh tests/integration/ -v
./run_tests.sh tests/e2e/ -v
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1.14 | 2026-01-29 | User management bug fixes |
| 1.1.15 | 2026-01-29 | Marketplace URL fix |
| 1.1.16 | 2026-01-29 | HTTPS certificate permissions |
| 1.1.17 | 2026-01-29 | HTTPS server certificate fix |
| 1.1.18 | 2026-01-29 | HTTPS key permissions, UI styling |
| 1.1.19 | 2026-01-29 | Test improvements, REQUIREMENTS.md, pre-commit hooks |
| 1.1.20 | 2026-01-29 | Delete button debugging improvements |
| 1.1.21 | 2026-01-29 | **HTTPS FIX: Remove ssl_bump directive**, debug logging |
