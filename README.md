# Squid Proxy Manager - Home Assistant Add-on

A Home Assistant add-on for managing Squid proxy instances on the same machine as Home Assistant. This add-on provides a user-friendly interface to create, configure, and manage Squid proxy instances with HTTPS support and basic authentication.

## Features

- **Docker-based Deployment**: Uses minimal scratch-based Docker images for security and efficiency
- **HTTPS Support**: Automatic certificate generation or use existing certificates
- **Basic Authentication**: User management with secure password hashing (bcrypt)
- **Config Flow UI**: Step-by-step wizard for easy setup
- **Service Actions**: Control proxy instances via Home Assistant services
- **Entity Status**: Real-time monitoring of proxy instance status
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

- Home Assistant 2023.11 or later
- Docker installed and running
- Access to Docker socket (`/var/run/docker.sock`)
- Python 3.10 or later

## Configuration

The integration uses a config flow wizard that guides you through:

1. **Instance Name**: Choose a unique name for your proxy instance
2. **Port Configuration**: Set the port number (1024-65535)
3. **HTTPS Certificate**: Enable HTTPS and configure certificates
4. **Initial User**: Create the first authentication user

## Services

The integration provides the following services:

- `squid_proxy_manager.start_instance`: Start a stopped proxy instance
- `squid_proxy_manager.stop_instance`: Stop a running proxy instance
- `squid_proxy_manager.restart_instance`: Restart a proxy instance
- `squid_proxy_manager.add_user`: Add a new authentication user
- `squid_proxy_manager.remove_user`: Remove an authentication user
- `squid_proxy_manager.update_certificate`: Update or renew HTTPS certificate
- `squid_proxy_manager.get_users`: Get list of users for a proxy instance

## Docker Image

The integration uses a minimal scratch-based Docker image. To build the image:

```bash
docker build -f custom_components/squid_proxy_manager/docker/Dockerfile.scratch -t squid-proxy-manager .
```

## Security Considerations

- Private keys and password files are stored with restricted permissions (600)
- Containers run as non-root user (UID 1000)
- Minimal container capabilities (only NET_BIND_SERVICE for ports < 1024)
- Resource limits are applied to prevent resource exhaustion
- All user input is validated before processing

## File Structure

```
custom_components/squid_proxy_manager/
├── manifest.json
├── __init__.py
├── config_flow.py
├── const.py
├── strings.json
├── translations/
│   └── en.json
├── platform/
│   ├── __init__.py
│   ├── proxy_entity.py
│   ├── coordinator.py
│   └── sensor.py
├── docker/
│   ├── __init__.py
│   ├── docker_manager.py
│   ├── squid_config.py
│   └── Dockerfile.scratch
├── security/
│   ├── __init__.py
│   ├── cert_manager.py
│   ├── auth_manager.py
│   └── security_utils.py
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
