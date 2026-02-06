# Squid Proxy Manager

Manage multiple Squid proxy instances directly from your Home Assistant sidebar. Create, configure, start/stop, and monitor proxy instances — all through a native HA dashboard.

![Add first proxy](https://raw.githubusercontent.com/rybnikov/HA_SQUID_PROXY/main/docs/gifs/00-add-first-proxy.gif)

## Features

- **Multiple proxy instances** — run several isolated Squid proxies on different ports simultaneously
- **HTTPS support** — enable TLS with auto-generated self-signed certificates per instance
- **User authentication** — per-instance basic auth with add/remove user management
- **Start/Stop control** — toggle each proxy instance independently from the settings page
- **Connectivity testing** — verify proxy access with built-in test tool (username, password, target URL)
- **Log viewer** — browse access and cache logs with search filtering, auto-refresh, and syntax highlighting
- **Native HA integration** — appears in the sidebar, uses Home Assistant design components, works via ingress

![Add HTTPS proxy](https://raw.githubusercontent.com/rybnikov/HA_SQUID_PROXY/main/docs/gifs/01-add-https-proxy.gif)

## Installation

1. Add this repository to Home Assistant:
   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Click the three dots menu → **Repositories**
   - Add: `https://github.com/rybnikov/HA_SQUID_PROXY`
   - Click **Add**

2. Install **Squid Proxy Manager** from the add-on store

3. Click **Start** — the add-on will appear in your sidebar

## Usage

### Create a Proxy Instance

1. Click **Add Instance** from the dashboard
2. Enter an instance name and port (1024–65535)
3. Optionally enable HTTPS
4. Optionally add initial users
5. Click **Create Instance**

### Manage Users

Each proxy instance has its own isolated user list. Navigate to instance settings and use the **Proxy Users** section to add or remove users.

### Test Connectivity

From the instance settings page, scroll to **Test Connectivity**. Enter credentials for a user of that instance, provide a target URL, and click **Test Connectivity** to verify the proxy is working.

### View Logs

Click **View Logs** on any instance to see access logs (with color-coded status codes, methods, and clients) or cache/debug logs (with severity highlighting). Use the search filter and auto-refresh toggle for monitoring.

## Network Configuration

Each proxy instance listens on its configured port. Make sure to:

- Expose the port in your Home Assistant host network configuration
- Configure your client applications to use `<HA_IP>:<PORT>` as the proxy address
- Provide the username and password if authentication is configured

## Support

For issues and feature requests: [GitHub Issues](https://github.com/rybnikov/HA_SQUID_PROXY/issues)
