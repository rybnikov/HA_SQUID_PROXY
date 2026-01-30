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

## Usage

### Creating an Instance
1. Click **+ Add Instance**.
2. Provide a unique name and port.
3. (Optional) Enable HTTPS.
4. Click **Create Instance**.

### Managing Users
1. Click the **Users** button on an instance card.
2. Add a username and password (min 8 characters).
3. The instance will automatically restart to apply the new users.

### Connectivity Test
To test your proxy, use `curl`:
```bash
curl -x http://user:pass@HA_IP:PORT http://google.com -v
```

## Development

Only Docker is required:

```bash
./setup_dev.sh    # Setup (one-time)
./run_tests.sh    # Run all tests
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for full guide.

## Documentation

- [DEVELOPMENT.md](DEVELOPMENT.md): Technical setup and development guide.
- [CONTEXT.md](CONTEXT.md): Architecture overview and project context.
- [TEST_PLAN.md](TEST_PLAN.md): Detailed testing scenarios and protocols.

## Security

- All proxies require authentication by default.
- Data is stored in the persistent `/data` partition.
- Modern encryption (`bcrypt`) is used for password storage.
- Automated security scanning (`bandit`, `safety`) is integrated into the development workflow.
