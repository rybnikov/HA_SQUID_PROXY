# Squid Proxy Manager - Home Assistant Add-on

A Home Assistant add-on for managing Squid proxy instances on the same machine as Home Assistant. This add-on provides a REST API and web interface to create, configure, and manage Squid proxy instances with HTTPS support and basic authentication.

## Features

- **Docker-based Deployment**: Uses minimal scratch-based Docker images for security and efficiency
- **HTTPS Support**: Automatic certificate generation or use existing certificates
- **Basic Authentication**: User management with secure password hashing (bcrypt)
- **REST API**: Full API for managing proxy instances
- **Ingress UI**: Web interface accessible through Home Assistant
- **Multiple Instances**: Manage multiple proxy instances simultaneously
- **Security Focus**: Implements security best practices including:
  - Secure file permissions
  - Non-root container execution
  - Minimal container capabilities
  - Resource limits
  - Input validation

## Installation

### Via HACS (Recommended)

1. Install [HACS](https://hacs.xyz) if you haven't already
2. Go to **HACS** → **Add-ons**
3. Click the three dots (⋮) in the top right → **Custom repositories**
4. Add repository:
   - **Repository**: `https://github.com/rybnikov/HA_SQUID_PROXY`
   - **Category**: Add-on
   - Click **Add**
5. Search for "Squid Proxy Manager" in HACS
6. Click **Download**
7. Go to **Settings** → **Add-ons** → **Squid Proxy Manager**
8. Configure and start the add-on

### Manual Installation (Add-on Repository)

1. Go to **Settings** → **Add-ons** → **Add-on Store**
2. Click the three dots (⋮) → **Repositories**
3. Add repository: `https://github.com/rybnikov/HA_SQUID_PROXY`
4. Find "Squid Proxy Manager" in the add-on store
5. Click **Install**
6. Configure and start the add-on

## Requirements

- Home Assistant Supervisor
- Docker support
- Network access for proxy functionality

## Configuration

Configure the add-on via the **Configuration** tab in the add-on settings:

```yaml
instances:
  - name: default
    port: 3128
    https_enabled: false
    users:
      - username: user1
        password: password123
  - name: https-proxy
    port: 8080
    https_enabled: true
    users:
      - username: user2
        password: password456

log_level: info
```

## API Endpoints

The add-on provides REST API endpoints:

- `GET /api/instances` - List all proxy instances
- `POST /api/instances` - Create a new proxy instance
- `POST /api/instances/{name}/start` - Start an instance
- `POST /api/instances/{name}/stop` - Stop an instance
- `DELETE /api/instances/{name}` - Remove an instance

## Building the Squid Docker Image

The Squid Docker image is **automatically built during add-on startup** if it doesn't already exist. No manual build is required.

**Manual build (optional):**

If you prefer to build the image manually:

```bash
docker build -f squid_proxy_manager/Dockerfile.squid -t squid-proxy-manager .
```

## Security Considerations

- Private keys and password files are stored with restricted permissions (600)
- Containers run as non-root user (UID 1000)
- Minimal container capabilities (only NET_BIND_SERVICE for ports < 1024)
- Resource limits are applied to prevent resource exhaustion
- All user input is validated before processing

## File Structure

```
squid_proxy_manager/
├── config.yaml          # Add-on configuration
├── Dockerfile           # Add-on container image
├── Dockerfile.squid     # Squid proxy scratch image
├── run.sh               # Startup script
├── README.md            # Add-on documentation
└── rootfs/app/
    ├── main.py          # API server
    ├── proxy_manager.py # Docker container management
    ├── squid_config.py  # Squid config generation
    ├── cert_manager.py  # Certificate management
    └── auth_manager.py  # User management
└── services/
    ├── __init__.py
    ├── services.yaml
    └── service_handler.py
```

## Troubleshooting

### Docker Not Available
- Ensure Docker is installed and running
- Check that the Docker socket is accessible at `/var/run/docker.sock`
- Verify the Home Assistant user has permission to access Docker

### Port Conflicts
- The integration checks for port conflicts during setup
- Ensure no other service is using the selected port

### Certificate Issues
- Self-signed certificates are generated automatically
- For production use, consider using Let's Encrypt or other CA certificates
- Certificate expiry is monitored and shown in entity attributes

## License

This integration is provided as-is for use with Home Assistant.
