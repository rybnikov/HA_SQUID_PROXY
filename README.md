# HA Squid Proxy Manager

[![CI](https://github.com/rbnkv/HA_SQUID_PROXY/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/rbnkv/HA_SQUID_PROXY/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Home Assistant add-on to manage multiple Squid proxy instances with independent configurations, users, and optional HTTPS support.

## Features

- **Multi-Instance Support**: Run multiple isolated Squid processes on different ports.
- **Web-Based Management**: Easy-to-use SPA for creating, starting, stopping, and deleting instances.
- **User Management**: Independent basic authentication (`htpasswd`) for each proxy.
- **HTTPS Proxy**: Support for SSL-enabled proxies with automatic self-signed certificate generation.
- **Log Viewer**: Live viewing of `access.log` and `cache.log` for each instance.
- **Persistence**: Configuration and cache are preserved across add-on updates and restarts.

## Installation

1. Add this repository to your Home Assistant Supervisor.
2. Install the "Squid Proxy Manager" add-on.
3. Start the add-on.
4. Access the "Open Web UI" to configure your first proxy instance.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                  Home Assistant                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Squid Proxy Manager Add-on (Docker Container)          │ │
│  │                                                          │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │ Web Server (aiohttp) on port 8099                │ │ │
│  │  │ • REST API: /api/instances                       │ │ │
│  │  │ • React SPA: Dashboard, Settings, Logs           │ │ │
│  │  └────────────────────────────────────────────────────┘ │ │
│  │           ↓ ↑                                             │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │ Proxy Manager (Python)                           │ │ │
│  │  │ • Instance lifecycle (create/start/stop/delete)  │ │ │
│  │  │ • Config generation for Squid                    │ │ │
│  │  │ • User authentication management                 │ │ │
│  │  │ • Certificate generation                         │ │ │
│  │  └────────────────────────────────────────────────────┘ │ │
│  │           ↓ ↓ ↓ ↓ ↓                                       │ │
│  │  ┌───────────────────────────────────────────────────┐  │ │
│  │  │ Squid Proxy Instances (isolated processes)       │  │ │
│  │  │                                                   │  │ │
│  │  │  Instance 1 (3128)  Instance 2 (3129)  Instance N  │  │ │
│  │  │  HTTP / HTTPS       HTTPS only         ...        │  │ │
│  │  │  Users: 2           Users: 3           Users: N   │  │ │
│  │  │  Config: unique     Config: unique     ...        │  │ │
│  │  │  Auth: isolated     Auth: isolated     ...        │  │ │
│  │  │  Logs: separate     Logs: separate     ...        │  │ │
│  │  └───────────────────────────────────────────────────┘  │ │
│  │                                                          │ │
│  │  Persistent Storage (/data)                            │ │
│  │  ├─ instance-1/                                        │ │
│  │  │   ├─ squid.conf       (Squid config)               │ │
│  │  │   ├─ passwd           (User database)              │ │
│  │  │   ├─ server.crt/.key  (HTTPS certs)                │ │
│  │  │   ├─ access.log       (HTTP logs)                  │ │
│  │  │   └─ cache.log        (Diagnostics)               │ │
│  │  ├─ instance-2/                                        │ │
│  │  │   └─ ...                                            │ │
│  │  └─ instance-n/                                        │ │
│  │      └─ ...                                            │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
│  Accessible via:                                            │
│  • Web UI: http://homeassistant:8099                       │
│  • Proxies: localhost:3128-3160 (forwarded to host)       │
└────────────────────────────────────────────────────────────────┘
```

### Key Features

**🔐 Security**
- Each proxy has independent user authentication (htpasswd MD5-crypt)
- Self-signed HTTPS certificates (server type, not CA)
- Non-root container execution (UID 1000:1000)
- Dropped capabilities (CAP_DROP all except NET_BIND_SERVICE)
- Read-only root filesystem

**⚡ Performance**
- Async API server (aiohttp with event loop)
- Parallel Squid processes (each instance independent)
- Efficient config generation and reload
- TanStack Query for optimized frontend state

**🛠️ Developer Experience**
- Docker-first development (no local system dependencies)
- Comprehensive testing (130+ tests in Docker)
- React SPA with TypeScript strict mode
- Playwright E2E tests (37 scenarios)
- Full Copilot/IDE support

## Usage

> **GIF Demos**: To capture workflow GIFs for this README, run:
> ```bash
> ./record_workflows.sh http://localhost:8100
> ```
> This will record interactive workflows and convert them to GIFs in `docs/gifs/`

### Dashboard Overview
![Dashboard](docs/gifs/00-dashboard.gif)

### Create Proxy Instance
![Create Proxy](docs/gifs/01-create-proxy.gif)

### Manage Users
![Manage Users](docs/gifs/02-manage-users.gif)

### Enable HTTPS
![Enable HTTPS](docs/gifs/03-enable-https.gif)

### View Logs
![View Logs](docs/gifs/04-view-logs.gif)

## Quick Start

Create your first proxy instance in seconds:

1. Open the Web UI dashboard
2. Click **+ Add Instance**
3. Enter instance name and port
4. Add users with authentication credentials
5. Click **Create** - your proxy is now running!

### Testing Your Proxy

Once a proxy is running, test it with `curl`:

```bash
# No authentication (will get 407 if required)
curl -x http://localhost:3128 http://google.com -v

# With authentication
curl -x http://localhost:3128 -U username:password http://google.com -v

# HTTPS proxy (ignore self-signed cert warnings)
curl --proxy-insecure -x https://localhost:3129 \
  -U username:password http://google.com -v
```

## Features in Detail

**Multiple Isolated Proxies**
- Run 1-13 independent Squid proxies simultaneously
- Each instance has unique configuration and user database
- Separate logs for each proxy
- Optional HTTPS on any instance

**User Management**
- Independent authentication per proxy
- Add/remove users instantly (MD5-crypt hashing)
- User isolation - alice on office-proxy cannot access remote-proxy

**HTTPS Support**
- Generate self-signed certificates with custom CN
- 365-day validity by default (configurable)
- Automatic cert generation and management
- Restart proxies with new HTTPS settings

**Log Monitoring**
- Real-time access logs with request details
- Cache diagnostics logs
- Auto-refresh every 5 seconds
- Search and download functionality

## Development

Only Docker is required:

```bash
./setup_dev.sh    # Setup (one-time)
./run_tests.sh    # Run all tests
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for full guide.

## Documentation

- [DEVELOPMENT.md](DEVELOPMENT.md): Technical setup and development guide.
- [REQUIREMENTS.md](REQUIREMENTS.md): User scenarios and acceptance criteria.
- [TEST_PLAN.md](TEST_PLAN.md): Detailed testing scenarios and protocols.
- [DESIGN_GUIDELINES.md](DESIGN_GUIDELINES.md): UI design patterns and components.

## Security

- All proxies require authentication by default.
- Data is stored in the persistent `/data` partition.
- MD5-crypt hashing for passwords (secure and Squid-compatible).
- Automated security scanning (`bandit`, Trivy) integrated in CI/CD.
