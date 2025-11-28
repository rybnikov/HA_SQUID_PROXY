# Home Assistant Squid Proxy Add-on

This add-on packages the Squid proxy daemon with a lightweight FastAPI-based management service and Ingress UI to provide configuration, lifecycle control, authentication management, certificate handling, and log visibility for HTTPS interception.

## Features
- Generates `squid.conf` from Home Assistant options stored in `/data/options.json`.
- Optional HTTP basic authentication backed by htpasswd stored at `/data/users.htpasswd`.
- Optional SSL bump support using a generated CA stored under `/ssl`.
- Lifecycle endpoints and UI controls to start, stop, restart, and reload Squid.
- Ingress UI for option management, SSL bump controls, user management, and live log tail for `access.log` and `cache.log` stored under `/data/logs`.

## File locations
- Squid configuration: `/data/squid.conf`
- Credentials: `/data/users.htpasswd`
- Logs: `/data/logs/access.log`, `/data/logs/cache.log`
- Cache storage: `/data/cache`
- Certificates: `/ssl/squid_ca.pem`, `/ssl/squid_ca.key`

## Development
1. Build the image:
   ```bash
   docker build -t ha-squid-proxy .
   ```
2. Run the container (requires host network privileges for Squid):
   ```bash
   docker run --rm -it -p 3128:3128 -p 8099:8099 -v $(pwd)/data:/data -v $(pwd)/ssl:/ssl --cap-add=NET_ADMIN ha-squid-proxy
   ```
3. The management API and UI are exposed on port `8099` and implement endpoints under `/` (see `app/main.py`). In Home Assistant the UI is available via Ingress.

## Ingress UI
- **Status & lifecycle:** Start, stop, restart, reload, and view PID/uptime/port/auth/SSL-bump state.
- **Options editor:** Update port, allowed CIDRs, auth toggle, SSL bump toggle, cache size, and CA auto-generation with validation to prevent empty networks.
- **Certificate management:** Generate/regenerate CA for SSL bumping and download the certificate.
- **User management:** Add/update/delete htpasswd users when authentication is enabled.
- **Logs:** Tail the latest entries of `access.log` and `cache.log` with refresh controls.

## Configuration options
The add-on uses Home Assistant options defined in `config.yaml`:
- `proxy_port`: Squid listening port (default `3128`).
- `allowed_networks`: CIDR list of clients permitted to connect.
- `enable_auth`: Toggle HTTP basic authentication (no default users created).
- `enable_ssl_bump`: Enable HTTPS interception; requires a CA certificate/key.
- `cache_size_mb`: Disk cache size in MB (default `512`).
- `generate_ca_on_first_run`: If true and SSL bump is enabled, the add-on will auto-generate a CA.
