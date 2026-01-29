# Technical Context: HA Squid Proxy Manager

## Architecture Overview

The HA Squid Proxy Manager is designed to provide multiple isolated Squid proxy instances within a single Home Assistant Add-on. 

### Process-Based Management

Instead of one container per proxy (which is difficult in HA add-ons), we run a single management process (`main.py`) that spawns multiple `squid` child processes.

- **Manager**: An `aiohttp` web server that provides an API and a Web UI.
- **Instances**: Each Squid instance has:
  - A unique `http_port` or `https_port`.
  - A dedicated configuration file (`squid.conf`).
  - A dedicated `htpasswd` file for authentication.
  - Independent logs (`access.log`, `cache.log`) and cache directory.

### Key Components

1.  **`ProxyInstanceManager`**: The heart of the application. It handles the lifecycle of Squid processes (start, stop, restart) and manages the metadata stored in `instance.json`.
2.  **`SquidConfigGenerator`**: Responsible for creating valid `squid.conf` files. It handles path quoting, port assignment, and authentication helper configuration.
3.  **`CertificateManager`**: Generates self-signed certificates for HTTPS-enabled proxy instances.
4.  **`AuthManager`**: Manages the `htpasswd` files used by Squid's `basic_ncsa_auth` helper.

## Data Persistence

All configuration and instance data is stored in the `/data` partition, which is persistent in Home Assistant:
- `/data/options.json`: Add-on options (including initial instances).
- `/data/squid_proxy_manager/`: Root directory for all instance data.
  - `<instance_name>/squid.conf`: Instance configuration.
  - `<instance_name>/passwd`: Instance users.
  - `<instance_name>/instance.json`: Instance metadata (port, status, etc.).
- `/data/squid_proxy_manager/logs/<instance_name>/`: Logs and cache swap for each instance.
- `/data/squid_proxy_manager/certs/<instance_name>/`: SSL certificates for HTTPS instances.

## Ingress Compatibility

The Web UI is served via Home Assistant Ingress. This requires:
- Handling of multiple slashes in paths (via `normalize_path_middleware`).
- Relative paths in the UI's JavaScript `fetch` calls.
- Listening on a fixed port (`8099`) as defined in `config.yaml`.

## Security Model

- **Authentication**: All proxy instances require basic authentication by default.
- **Isolated Credentials**: Each instance can have its own set of users.
- **Restricted Access**: The manager UI should be accessed through Home Assistant's authenticated session.
- **Process Isolation**: While running in the same container, Squid processes are separated by configuration and data directories.
