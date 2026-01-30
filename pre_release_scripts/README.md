# Pre-Release Scripts

## Recording Workflows (GIF Generation)

### Quick Start

```bash
# Single command - handles everything
./record_workflows_full.sh
```

That's it! The script will:
1. ✅ Stop any existing dev addon
2. ✅ Start a fresh addon instance
3. ✅ Wait for addon health check
4. ✅ Record all workflows as GIFs using Playwright + ffmpeg
5. ✅ Stop the addon

### What Gets Generated

GIFs are saved to `../docs/gifs/`:

| Workflow | Duration | File |
|----------|----------|------|
| Add proxy to dashboard + users | ~2 min | `00-add-first-proxy.gif` |
| Add HTTPS proxy + cert + users | ~2.5 min | `01-add-https-proxy.gif` |

### Advanced: Manual Control

If you need more control over the process:

```bash
# 1. Start addon manually
../run_addon_local.sh start

# 2. Run recording (addon must be running)
./record_workflows.sh http://localhost:8100

# 3. Stop addon when done
../run_addon_local.sh stop
```

### Script Details

**record_workflows_full.sh** (Master orchestrator)
- Manages addon lifecycle
- Handles health checks (max 120s timeout)
- Automatic cleanup on completion or error
- Color-coded progress output

**record_workflows.sh** (Docker wrapper)
- Launches `ha_squid_proxy-e2e-runner` Docker container
- Uses host network for addon access
- Streams output for debugging

**record_workflows_impl.py** (Playwright automation)
- Actual browser automation logic
- Records two complete workflows
- Converts screenshots to GIF with ffmpeg
- Error handling and timeouts

### Troubleshooting

**"Docker is not running"**
```bash
# Start Docker Desktop on macOS
open -a Docker
```

**"Connection refused" errors**
- The script uses `--network host` to access localhost addon
- If Docker fails to connect, verify:
  - Addon is running: `curl http://localhost:8100/health`
  - Docker has host network access

**"Timeout waiting for addon"**
- Addon is taking >120s to start (normal on first run)
- Increase `MAX_HEALTH_CHECKS` in `record_workflows_full.sh`
- Check addon logs: `../run_addon_local.sh logs`

**"Form field selector timeout"**
- Modal or form not loading in expected time
- Check actual UI structure to validate selectors
- May need to adjust waits in `record_workflows_impl.py`

### Development

To modify workflows or recording behavior:

```python
# Edit: record_workflows_impl.py

# Workflow 1: Change instance name, port, users, etc.
async def record_workflow_1(page):
    # ... modify steps here ...

# Workflow 2: Change HTTPS settings, cert params, etc.
async def record_workflow_2(page):
    # ... modify steps here ...
```

All workflows use:
- `page.goto()` for navigation
- `page.locator()` for element selection
- `page.fill()` for form input
- `page.click()` for button clicks
- Custom waits with regex-based selectors

### Docker Images

The scripts use these Docker images (auto-built if missing):

- `ha_squid_proxy-e2e-runner`: Based on `tests/Dockerfile.test`
  - Contains: Python 3.11, Playwright, ffmpeg, pytest
  - Size: ~450MB
  - Purpose: UI automation and GIF generation

## Release Checklist

Before releasing a version:

```bash
# 1. Run full test suite
../run_tests.sh

# 2. Record workflows (generates GIFs)
./record_workflows_full.sh

# 3. Verify GIFs in docs/gifs/
ls -lh ../docs/gifs/

# 4. Commit & push
git add ../docs/gifs/
git commit -m "release: update workflow GIFs"
git push origin main
```

## Maintenance

Keep these files up-to-date:

- **record_workflows_full.sh** - Change if addon health check URL changes
- **record_workflows.sh** - Change if Docker configuration changes
- **record_workflows_impl.py** - Change if UI workflows or steps change

All changes should be tested with:
```bash
./record_workflows_full.sh
```

---

**Last Updated**: January 2026
**Maintainer**: HA Squid Proxy Team
