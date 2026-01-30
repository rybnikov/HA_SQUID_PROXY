# HA Squid Proxy Manager

[![CI](https://github.com/rbnkv/HA_SQUID_PROXY/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/rbnkv/HA_SQUID_PROXY/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Manage multiple Squid HTTP/HTTPS proxies with a beautiful web dashboard.** Create isolated proxy instances with independent user authentication, HTTPS support, and real-time monitoring—all from your Home Assistant instance.

Perfect for:
- 🔀 **Load balancing** traffic across multiple proxy servers
- 🏢 **Multi-tenant networks** with isolated users per proxy
- 🔒 **Secured connections** with HTTPS and user authentication
- 📊 **Traffic monitoring** with real-time access logs
- 🛡️ **Content filtering** at the proxy level

## What You Get

| Feature | Description |
|---------|-------------|
| ✅ Easy Web Dashboard | Create, manage, and monitor proxies without touching config files |
| ✅ Multiple Proxies | Run 1-13 isolated proxy instances simultaneously |
| ✅ User Authentication | Independent user accounts for each proxy instance |
| ✅ HTTPS Support | Enable encrypted proxy connections with auto-generated certificates |
| ✅ Live Logs | Monitor proxy traffic, search logs, and track requests |
| ✅ Persistent Storage | Your proxy configs survive add-on restarts |
| ✅ No Restart Required | Start, stop, and modify proxies instantly |

## Get Started in 60 Seconds

### Step 1: Install

1. Add repository: `https://github.com/rbnkv/HA_SQUID_PROXY`
2. Install "Squid Proxy Manager" from Add-on Store
3. Click "Start" and wait for "Started"
4. Click "Open Web UI"

### Step 2: Create Your First Proxy

![Dashboard](docs/gifs/00-dashboard.gif)

Click **+ Add Instance** and fill in:
- **Name**: "office" (or any name)
- **Port**: 3128
- **Toggle HTTPS**: Off for now

Click **Create** — your proxy is running!

### Step 3: Add Users

![Add Users](docs/gifs/02-manage-users.gif)

Click on your proxy → **Settings** → **Users tab**

Add authentication:
- **Username**: alice
- **Password**: secure_password

Click **Add User** — users can now authenticate to your proxy.

### Step 4: Test It Works

```bash
# Test with authentication
curl -x http://localhost:3128 -U alice:secure_password http://google.com

# If it works, you'll see Google's HTML response
```

Done! Your proxy is running and authenticated.

## Main Features in Action

### 1. Dashboard — View All Proxies at a Glance

See all running proxies with status, port, and HTTPS indicator. Quick-action buttons for each proxy.

### 2. Create Proxies — No Config Files Needed

![Create Proxy](docs/gifs/01-create-proxy.gif)

Give it a name, pick a port, optionally enable HTTPS. That's it.

### 3. Manage Users — Instant Authentication

![Manage Users](docs/gifs/02-manage-users.gif)

Add/remove users per proxy. Each user can only access their assigned proxy. Real-time changes.

### 4. Enable HTTPS — Encrypted Connections

![Enable HTTPS](docs/gifs/03-enable-https.gif)

Toggle HTTPS on and a certificate is auto-generated. Restart happens silently in the background.

### 5. Monitor Traffic — See What's Being Proxied

![View Logs](docs/gifs/04-view-logs.gif)

Access logs show every request: client IP, timestamp, target URL, response status. Search and filter in real-time.

## Real-World Use Cases

### Multi-Tenant Office Network
- Office staff on ports 3128 (with auth)
- Guest network on port 3129 (different users)
- Management on port 3130 (HTTPS + restricted)

Each group has isolated users. No cross-pollination.

### Load Balancing & Failover
- Run 3 proxy instances
- Route traffic across them
- If one fails, the others keep working

### Secure Remote Access
- Enable HTTPS on a proxy
- Create strong authentication
- Remote users connect securely
- Monitor who accesses what

### Content Filtering at Scale
- Multiple proxies with different policies
- Users assigned to specific proxies
- Each proxy can filter differently
- Monitor each one independently

## Technical Overview

**Behind the scenes:**
- **Web Server** (aiohttp): Dashboard + REST API on port 8099
- **Proxy Manager** (Python): Creates/manages Squid instances
- **Squid Proxies** (isolated): 1-13 independent processes per port
- **Storage** (/data): Configs, users, certs, logs (persistent across restarts)

Each proxy instance is **100% isolated**:
- Own configuration file
- Own user database
- Own HTTPS certificate (if enabled)
- Own access/cache logs
- Can be stopped/started independently

## Frequently Asked Questions

**Q: Can I run multiple proxies at the same time?**
Yes! You can run up to 13 proxies on different ports (3128-3140). Each is completely independent.

**Q: Do users share passwords across proxies?**
No. Each proxy has its own user database. "alice" on office-proxy is different from "alice" on remote-proxy.

**Q: Can I enable HTTPS on just one proxy?**
Yes. Some proxies can be HTTP, others HTTPS. Mix and match as needed.

**Q: What if I restart the add-on?**
All your proxy configurations, users, and logs are saved. They'll be back exactly as they were.

**Q: How do I use the proxy from my computer?**
Configure your app to use: `http://homeassistant:3128` (or the port you chose)
Enter username and password when prompted (if you added users).

**Q: Is this secure?**
Yes. Passwords are hashed (MD5-crypt), add-on runs non-root, HTTPS is supported. See Security section.

**Q: Can I monitor who's using my proxies?**
Yes. Each proxy has access logs showing client IP, timestamp, URL, response status. Real-time search available.

## Technical Specs

| Feature | Details |
|---------|---------|
| **Max Proxies** | 1-13 per container (ports 3128-3140) |
| **Port Range** | 3128-3140 (configurable per instance) |
| **Authentication** | MD5-crypt htpasswd (Squid standard) |
| **HTTPS Certs** | Self-signed, auto-generated, 365-day validity |
| **Users per Proxy** | Unlimited |
| **Ports Used** | 8099 (web dashboard) + proxy ports |
| **Storage** | Persistent /data volume |
| **Restart Behavior** | All configs preserved |
| **CPU/Memory** | ~50MB base + ~20MB per proxy instance |

## Compatibility

- **Home Assistant**: 2024.1.0+
- **Docker**: Required
- **Network**: Proxies must be accessible from client devices

## Support & Troubleshooting

**Issue: "Connection Refused" when testing proxy**
- Verify the instance is running (shows "Running" badge)
- Check you're using the correct port (default 3128)
- Verify port forwarding if accessing remotely

**Issue: "407 Proxy Authentication Required"**
- This is normal! It means authentication is required
- Add users in the Settings → Users tab
- Use correct username:password in your proxy settings

**Issue: HTTPS shows certificate warning**
- This is expected! Self-signed certificates always warn
- The connection is encrypted, just untrusted
- Use `--proxy-insecure` in curl or accept the warning in your browser

**Issue: Can't reach proxy from another device**
- Port forwarding must be configured
- Firewall rules must allow proxy port (3128, 3129, etc.)
- Device must be on same network or have port forwarding

For more help, see [REQUIREMENTS.md](REQUIREMENTS.md) for detailed scenarios and [DESIGN_GUIDELINES.md](DESIGN_GUIDELINES.md) for UI documentation.
