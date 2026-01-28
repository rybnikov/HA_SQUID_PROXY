# Squid Proxy Manager Add-on

Home Assistant add-on for managing multiple Squid proxy instances with HTTPS support and basic authentication.

## Features

- 🐳 Docker-based proxy instance management
- 🔒 HTTPS certificate generation and management
- 👤 Basic authentication with user management
- 🎨 Web UI via Home Assistant ingress
- ⚙️ Multiple proxy instances support
- 🔐 Security-focused implementation

## Installation

1. Add this repository to Home Assistant:
   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Click the three dots (⋮) → **Repositories**
   - Add: `https://github.com/rybnikov/HA_SQUID_PROXY`
   - Click **Add**

2. Install the add-on:
   - Find "Squid Proxy Manager" in the add-on store
   - Click **Install**
   - Wait for installation to complete

3. Configure:
   - Click **Configuration** tab
   - Configure your proxy instances
   - Click **Save**

4. Start:
   - Click **Start**
   - The add-on will be available via ingress

## Configuration

Edit the configuration in the add-on's **Configuration** tab:

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

## Usage

After starting the add-on, access it via:
- **Home Assistant UI**: The add-on will appear in the sidebar
- **Ingress**: Available through Home Assistant's ingress feature

## Requirements

- Home Assistant Supervisor
- Docker support
- Network access for proxy functionality

## Squid Proxy Image

The add-on automatically builds the minimal scratch-based Squid Docker image during startup if it doesn't already exist. This happens automatically when you start the add-on for the first time.

**Note:** The initial build may take several minutes as it compiles Squid from source. Subsequent starts will be faster as the image will already exist.

If you prefer to build the image manually before starting the add-on:

```bash
docker build -f Dockerfile.squid -t squid-proxy-manager .
```

## Support

For issues and questions, visit: https://github.com/rybnikov/HA_SQUID_PROXY/issues
