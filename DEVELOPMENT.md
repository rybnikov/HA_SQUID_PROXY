# Development Guide: HA Squid Proxy Manager

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- `pre-commit`

## Setup Development Environment

1. **Clone the repository**
2. **Run the setup script**:
   ```bash
   ./setup_dev.sh
   ```
   This script will:
   - Create a Python virtual environment.
   - Install all necessary dependencies.
   - Install `pre-commit` hooks.

## Project Structure

- `squid_proxy_manager/rootfs/app/`: Core application logic.
- `tests/unit/`: Component-level unit tests.
- `tests/integration/`: Process-based tests with real/fake Squid.
- `tests/e2e/`: Full Docker-based traffic and UI tests with Playwright.

## Code Quality & Security

We use `pre-commit` to ensure code quality and security before every commit.

```bash
# Run all linters and security checks
pre-commit run --all-files

# Specific tools
ruff check .
black .
mypy .
bandit -c pyproject.toml -r .
```

## Testing

### Run ALL Tests in Docker (Recommended)

All tests run in Docker with full network access - **no tests skipped**.

```bash
# Run ALL tests (unit + integration + e2e)
./run_tests.sh

# Run only unit + integration tests (faster)
./run_tests.sh unit

# Run only E2E tests (with real Squid addon)
./run_tests.sh e2e
```

### Test Architecture

| Test Type | Location | What It Tests | Squid |
|-----------|----------|---------------|-------|
| Unit | `tests/unit/` | Config generation, auth, certs | None |
| Integration | `tests/integration/` | API, process management | Real (in Docker) |
| E2E | `tests/e2e/` | Full flows, UI (Playwright) | Real addon |

### Local Tests (Optional)

Run tests locally during development. Some tests may be skipped due to sandbox restrictions.

```bash
# Run locally (some tests may skip)
./run_tests.sh local

# Run specific tests locally
./run_tests.sh local tests/unit/test_squid_config.py
```

### Pre-commit Hooks

Pre-commit automatically runs fast unit tests before each commit:
- Unit tests (all)
- Integration tests (network-independent only)

To skip hooks temporarily:
```bash
git commit --no-verify -m "message"
```

## E2E Test Infrastructure

E2E tests use Docker Compose with:

1. **addon** service: Real Squid Proxy Manager
2. **e2e-runner** service: Playwright + pytest

```yaml
# docker-compose.test.yaml
services:
  addon:      # Real add-on with Squid
  e2e-runner: # Playwright tests against addon
```

## Troubleshooting

### View Squid Logs
```bash
# In running addon container
docker exec -it <container> cat /data/squid_proxy_manager/logs/<instance>/cache.log
```

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Tests skipped | Running locally without Docker | Use `./run_tests.sh` (Docker) |
| Port conflict | Port already in use | Use different port or stop other process |
| HTTPS fails | ssl_bump in config | Remove ssl_bump directive |
| Delete not working | window.confirm() blocked | Use custom modal |

### Debug E2E Tests

```bash
# Run with visible browser (headed mode)
docker compose -f docker-compose.test.yaml run --rm e2e-runner \
  pytest tests/e2e -v --headed

# Run single test
docker compose -f docker-compose.test.yaml run --rm e2e-runner \
  pytest tests/e2e/test_https_ui.py::test_https_instance_stays_running -v
```
