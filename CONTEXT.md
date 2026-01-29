# Technical Context: HA Squid Proxy Manager

> **Quick Reference**: See `.cursorrules` for bug patterns, code examples, and checklist.

## System Components

### 1. Web Server (`main.py`)
- **Framework**: aiohttp (async)
- **Port**: 8099 (fixed, configured in config.yaml)
- **UI**: SPA embedded as Python string (HTML/CSS/JS inline)
- **Ingress**: Accessed via Home Assistant proxy

### 2. Process Manager (`proxy_manager.py`)
- **Class**: `ProxyInstanceManager`
- **Process Model**: `subprocess.Popen` with `-N` (no daemon)
- **State**: `instance.json` per instance + in-memory `processes` dict
- **Lifecycle**: create → start → stop → remove

### 3. Config Generator (`squid_config.py`)
- **Class**: `SquidConfigGenerator`
- **Output**: `/data/squid_proxy_manager/<name>/squid.conf`
- **HTTPS**: Uses `https_port` with `tls-cert`/`tls-key` (NO ssl_bump!)

### 4. Certificate Manager (`cert_manager.py`)
- **Library**: `cryptography`
- **Type**: Self-signed server certificate (NOT CA)
- **Files**: `server.crt`, `server.key` in instance directory
- **Permissions**: `0o644` for both (squid needs read access)

### 5. Auth Manager (`auth_manager.py`)
- **Format**: htpasswd (MD5-crypt / APR1)
- **File**: `/data/squid_proxy_manager/<name>/passwd`
- **Squid Helper**: `/usr/lib/squid/basic_ncsa_auth`

## API Endpoints

| Method | Endpoint | Action |
|--------|----------|--------|
| GET | `/api/instances` | List all instances |
| POST | `/api/instances` | Create instance |
| DELETE | `/api/instances/<name>` | Remove instance |
| POST | `/api/instances/<name>/start` | Start instance |
| POST | `/api/instances/<name>/stop` | Stop instance |
| POST | `/api/instances/<name>/restart` | Restart instance |
| PUT | `/api/instances/<name>/settings` | Update settings |
| GET | `/api/instances/<name>/users` | List users |
| POST | `/api/instances/<name>/users` | Add user |
| DELETE | `/api/instances/<name>/users/<user>` | Remove user |
| GET | `/api/instances/<name>/logs` | Get logs |
| POST | `/api/instances/<name>/test` | Test connectivity |

## Squid Configuration

### HTTP Instance
```
http_port [::]:3128
cache_dir ufs /data/.../cache 100 16 256
access_log /data/.../access.log
cache_log /data/.../cache.log
auth_param basic program /usr/lib/squid/basic_ncsa_auth /data/.../passwd
auth_param basic realm Squid Proxy
acl authenticated proxy_auth REQUIRED
http_access allow authenticated
http_access deny all
```

### HTTPS Instance (CRITICAL: no ssl_bump!)
```
https_port [::]:3129 tls-cert=/data/.../server.crt tls-key=/data/.../server.key
# NOTE: NO ssl_bump directive - it requires CA signing cert!
```

## Test Infrastructure

### Unit Tests (`tests/unit/`)
- Mock filesystem, no real processes
- Test config generation, auth logic, cert generation
- Key: `test_squid_config_https.py` - verifies NO ssl_bump

### Integration Tests (`tests/integration/`)
- Uses `fake_squid` script (shell script that accepts args)
- Tests API endpoints with mocked manager
- Network tests skipped in sandbox (use `@pytest.mark.network`)

### E2E Tests (`tests/e2e/`)
- **Real Squid**: Docker container with actual squid binary
- **Browser**: Playwright (Chromium)
- **Compose**: `docker-compose.test.yaml`
- Key: `test_https_ui.py` - verifies HTTPS instance stays running

## Common Pitfalls

1. **ssl_bump**: Even `ssl_bump none all` requires a signing CA cert. Don't use it.
2. **window.confirm()**: Blocked in HA ingress iframe. Use custom modal.
3. **File permissions**: Squid runs as `squid` user, needs read access to certs.
4. **Port conflicts**: Each instance needs unique port in 3128-3140 range.
5. **Path quoting**: Squid 5.9 doesn't like quoted paths in `tls-cert=`/`tls-key=`.

## Debugging

### Check Squid Logs
```bash
# In container
cat /data/squid_proxy_manager/logs/<name>/cache.log
```

### Common Errors
| Error | Cause | Fix |
|-------|-------|-----|
| `FATAL: No valid signing certificate` | ssl_bump in config | Remove ssl_bump directive |
| `407 Proxy Authentication Required` | Wrong user/pass or passwd file | Check passwd path, verify user exists |
| `curl: (60) SSL certificate problem` | Self-signed cert | Use `curl --proxy-insecure` |
