# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HA Squid Proxy Manager is a **Home Assistant Add-on** (not a custom component) that manages multiple Squid proxy instances via a web dashboard. It runs in a Docker container and uses `subprocess.Popen` to spawn isolated Squid processes.

## Build & Test Commands

```bash
# Initial setup (Docker required, no local Python venv needed)
./setup_dev.sh

# Run all tests (unit + integration + E2E) in Docker
./run_tests.sh

# Run specific test suites
./run_tests.sh unit     # Unit + integration (~60s)
./run_tests.sh e2e      # E2E browser tests (~180s)

# Run single test
pytest tests/unit/test_proxy_manager.py::test_create_instance -v
pytest tests/e2e/test_scenarios.py::test_scenario_1 -n 1 -v

# Lint checks (must pass before commit)
docker compose -f docker-compose.test.yaml --profile lint up --build --abort-on-container-exit --exit-code-from lint-runner

# Frontend development
cd squid_proxy_manager/frontend
npm run dev              # Dev server at :5173
npm run dev:mock         # Mock mode (no backend)
npm run build            # Production build
npm run test             # Vitest unit tests
npm run lint             # ESLint
npm run typecheck        # TypeScript check

# Local addon testing (standalone)
./run_addon_local.sh start   # Start addon at http://localhost:8099
./run_addon_local.sh logs    # View logs
./run_addon_local.sh stop    # Stop addon

# Local addon + Home Assistant Core (one command, only Docker needed)
./run_addon_local.sh start --ha   # Addon + HA Core (login: admin/admin)
./run_addon_local.sh logs --ha    # View all logs
./run_addon_local.sh stop --ha    # Stop everything
./run_addon_local.sh clean --ha   # Remove containers + volumes

# GIF recording (fully dockerized, no local Playwright/ffmpeg needed)
./pre_release_scripts/record_workflows.sh --start-ha   # Cold start + record + stop
./pre_release_scripts/record_workflows.sh --ha          # Record against running stack
./pre_release_scripts/record_workflows.sh               # Standalone (no HA sidebar)
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Docker Container (HA Add-on)                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │ main.py (aiohttp server on :8099)               │   │
│  │  - REST API: /api/instances/*                   │   │
│  │  - React SPA frontend                           │   │
│  └─────────────────────────────────────────────────┘   │
│           │ subprocess.Popen                            │
│  ┌────────┴────────┬────────────────┐                  │
│  │ squid -N -f ... │ squid -N -f ...│ (N instances)    │
│  │ :3128           │ :3129          │                  │
│  └─────────────────┴────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

### Key Backend Files

| File | Purpose |
|------|---------|
| `squid_proxy_manager/rootfs/app/main.py` | aiohttp API server + request handlers |
| `squid_proxy_manager/rootfs/app/proxy_manager.py` | `ProxyInstanceManager` - process lifecycle |
| `squid_proxy_manager/rootfs/app/squid_config.py` | `SquidConfigGenerator` - config file generation |
| `squid_proxy_manager/rootfs/app/auth_manager.py` | `AuthManager` - htpasswd user management |
| `squid_proxy_manager/rootfs/app/cert_manager.py` | `CertificateManager` - self-signed cert generation |

### Frontend Structure

React 19 + TypeScript + Vite + Tailwind CSS + HA Web Components in `squid_proxy_manager/frontend/`:
- `src/features/instances/` - DashboardPage, ProxyCreatePage, InstanceSettingsPage
- `src/features/instances/tabs/` - Settings tab panels (config, users, certs, logs, test, danger)
- `src/ui/ha-wrappers/` - Home Assistant component wrappers (HAButton, HASwitch, HACard, HADialog, etc.)
- `src/api/client.ts` - API client with mock mode support
- `src/ha-panel.tsx` - HA custom panel entry point

### Data Paths

```
/data/squid_proxy_manager/
├── <instance_name>/
│   ├── squid.conf      # Generated Squid config
│   ├── passwd          # htpasswd file (UNIQUE per instance!)
│   ├── instance.json   # Instance metadata
│   ├── server.crt      # HTTPS cert (if enabled)
│   └── server.key      # HTTPS key (if enabled)
└── logs/<instance_name>/
    ├── access.log
    └── cache.log
```

## HA Web Component Gotchas

### ha-button Modern API
```tsx
// WRONG - old boolean props
<ha-button raised outlined>Click</ha-button>

// CORRECT - use appearance attribute
<ha-button appearance="accent">Primary</ha-button>   // variant="primary"
<ha-button appearance="outlined">Outlined</ha-button> // outlined prop
<ha-button appearance="plain">Default</ha-button>     // default/secondary
```

### ha-button Slot Names
```tsx
// WRONG - slot="icon" does NOT exist in ha-button shadow DOM
<ha-icon slot="icon" icon="mdi:plus"></ha-icon>

// CORRECT - shadow DOM has slots: start, (default), end
<ha-icon slot="start" icon="mdi:plus"></ha-icon>
```

### React 19 + Custom Elements
React 19 sets custom element properties (not attributes). So `getAttribute('icon')` returns null even though the `icon` property works. This is expected behavior — don't try to "fix" it.

### HA Ingress Service Worker Caching
HA uses Workbox SW that aggressively caches assets. When testing new frontend builds:
1. Unregister all Service Workers
2. Clear all caches (Cache Storage API)
3. Hard reload

## Docker Build Gotchas

- `docker compose up -d --build` can use cached layers — use `--no-cache` when `COPY rootfs/ /` changes aren't picked up
- `docker compose restart` does NOT rebuild — need `build --no-cache` then `up -d`
- The correct rebuild command: `docker compose -f docker-compose.test.yaml --profile ha build --no-cache addon`

## Instance State Persistence

Each instance stores `desired_state` ("running"/"stopped") in `instance.json`. On addon restart, `restore_desired_states()` in `proxy_manager.py` auto-starts/stops instances based on their last known state. Important: save desired_state in ALL code paths of `stop_instance()`, including early returns.

## Critical Bug Patterns to Avoid

### 1. HTTPS Configuration - NO ssl_bump

```python
# WRONG - causes "FATAL: No valid signing certificate"
config_lines.append("ssl_bump none all")  # DELETE THIS

# CORRECT - simple HTTPS proxy
config_lines.append(f"https_port {port} tls-cert={cert_path} tls-key={key_path}")
# NO ssl_bump directive!
```

### 2. Window Dialogs in HA Ingress

```javascript
// WRONG - window.confirm() blocked in Home Assistant iframe
if (window.confirm('Delete?')) { ... }

// CORRECT - use custom modal
document.getElementById('deleteModal').style.display = 'block';
```

### 3. Instance Auth Isolation

```python
# WRONG - shared auth breaks isolation
auth_path = "/data/squid_proxy_manager/passwd"

# CORRECT - each instance has unique passwd
auth_path = f"/data/squid_proxy_manager/{instance_name}/passwd"
```

## Testing Requirements

All tests must pass before merge (enforced by CI):
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- E2E tests: `tests/e2e/` (Playwright + real addon container)

E2E tests use `data-testid` attributes for selectors:
```tsx
<button data-testid="instance-create-button">Create</button>
```
```python
await page.click('[data-testid="instance-create-button"]')
```

## Version Bump (3 places)

1. `squid_proxy_manager/config.yaml` → `version: "X.Y.Z"`
2. `squid_proxy_manager/Dockerfile` → `io.hass.version="X.Y.Z"`
3. `squid_proxy_manager/frontend/package.json` → `"version": "X.Y.Z"`

## Documentation Sources

- `DEVELOPMENT.md` - Build, test, debug workflows
- `REQUIREMENTS.md` - Feature requirements, user scenarios
- `TEST_PLAN.md` - Test coverage, procedures
- `DESIGN_GUIDELINES.md` - UI/frontend patterns
- `CLAUDE.md` - Quick reference for AI agents (this file)
