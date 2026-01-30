# Development Guide: HA Squid Proxy Manager

## Prerequisites

**Only Docker is required.** IDE plugins handle linting/formatting.

| Requirement | Purpose |
|-------------|---------|
| Docker + Docker Compose | Run tests, build addon |
| IDE with Python support | Code editing, linting (optional) |

## Quick Start

```bash
# 1. Clone and setup
git clone <repo>
cd HA_SQUID_PROXY
./setup_dev.sh

# 2. Run all tests
./run_tests.sh
```

That's it. No Python venv, no local dependencies.

## Project Structure

```
squid_proxy_manager/
├── rootfs/app/          # Core Python application
│   ├── main.py          # API + UI server
│   ├── proxy_manager.py # Process management
│   ├── squid_config.py  # Config generation
│   ├── auth_manager.py  # htpasswd management
│   └── cert_manager.py  # SSL certificates
├── frontend/            # React SPA (Vite + Tailwind)
├── config.yaml          # HA addon config
└── Dockerfile           # Addon container

tests/
├── unit/                # Fast, no dependencies
├── integration/         # With real Squid
├── e2e/                 # Full UI tests (Playwright)
└── Dockerfile.test      # Test runner container
```

## Testing

### Run All Tests (Recommended)

```bash
./run_tests.sh              # ALL tests in Docker (unit + integration + e2e)
```

### Specific Test Suites

```bash
./run_tests.sh unit         # Unit + integration only (faster, ~1 min)
./run_tests.sh ui           # Frontend lint/typecheck/unit tests
./run_tests.sh e2e          # E2E only with real Squid addon (~3 min)
```

### Test Architecture

| Suite | Container | Squid | Browser |
|-------|-----------|-------|---------|
| Unit | test-runner | None | None |
| Integration | test-runner | Real | None |
| E2E | e2e-runner + addon | Real addon | Playwright |

All tests run in Docker with full network access. **No tests are skipped.**

## IDE Setup (Optional but Recommended)

### VS Code / Cursor

Install these extensions for in-editor linting and formatting:

| Extension | Purpose |
|-----------|---------|
| Python (ms-python.python) | Language support |
| Black Formatter | Auto-format on save |
| Ruff | Fast linting |

Settings (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "/usr/bin/python3",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true
  },
  "ruff.lint.run": "onSave"
}
```

### PyCharm

1. Settings → Tools → Black: Enable "On save"
2. Settings → Editor → Inspections: Enable Ruff

## Code Quality

### Run Linters in Docker

```bash
# Format code
docker run --rm -v $(pwd):/code -w /code python:3.11-slim \
  sh -c "pip install black ruff && black . && ruff check --fix ."

# Type checking
docker run --rm -v $(pwd):/code -w /code python:3.11-slim \
  sh -c "pip install mypy aiohttp types-requests && mypy squid_proxy_manager/rootfs/app"
```

### Pre-commit (Optional)

If you want pre-commit hooks locally, you need Python installed:

```bash
pip install pre-commit
pre-commit install
```

Otherwise, rely on IDE plugins and Docker tests.

## Building the Addon

```bash
# Build addon image locally
docker build -t squid-proxy-manager ./squid_proxy_manager

# Test the built image
docker run -p 8099:8099 -v squid-data:/data squid-proxy-manager
```

## Debugging

### View Container Logs

```bash
# During E2E tests
docker compose -f docker-compose.test.yaml logs -f addon

# View Squid instance logs
docker compose -f docker-compose.test.yaml exec addon \
  cat /data/squid_proxy_manager/logs/<instance>/cache.log
```

### Run Single E2E Test

```bash
docker compose -f docker-compose.test.yaml --profile e2e run --rm e2e-runner \
  pytest tests/e2e/test_https_ui.py::test_https_instance_stays_running -v
```

### Interactive Shell in Test Container

```bash
docker compose -f docker-compose.test.yaml --profile unit run --rm test-runner bash
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Tests fail on first run | Images not built | Run `./setup_dev.sh` |
| Port already in use | Previous test didn't cleanup | `docker compose down -v` |
| HTTPS proxy crashes | ssl_bump in config | Check squid_config.py |
| Delete button not working | window.confirm() blocked | Use custom modal |

## Release Checklist

1. Run all tests: `./run_tests.sh`
2. Update version in:
   - `squid_proxy_manager/config.yaml`
   - `squid_proxy_manager/Dockerfile`
   - `squid_proxy_manager/rootfs/app/main.py`
3. Commit and tag: `git tag -a vX.Y.Z`
4. Push: `git push origin main --tags`
