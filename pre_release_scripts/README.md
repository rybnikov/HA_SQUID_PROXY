# Pre-Release Scripts

## Recording Workflows (GIF Generation)

### Quick Start

```bash
# Single command - handles everything
./record_workflows.sh
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
ADDON_URL=http://localhost:8099 ./record_workflows.sh

# Optional: customize pace (seconds between actions)
RECORDING_MIN_ACTION_PAUSE=2 ./record_workflows.sh

# Optional: customize GIF fps (lower = longer per frame)
RECORDING_GIF_FPS=1 ./record_workflows.sh

# Optional: clean addon data before recording (default: 1)
RECORDING_CLEAN_DATA=1 ./record_workflows.sh

# 3. Stop addon when done
../run_addon_local.sh stop
```

### Script Details

**record_workflows.sh** (Unified pipeline)
- Manages addon lifecycle
- Handles health checks and cleanup
- Launches Docker container for recording
- Cross-platform addon access (macOS uses `host.docker.internal`)
- Color-coded progress output

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
- On macOS, the script uses `host.docker.internal` to reach the addon
- If Docker fails to connect, verify:
  - Addon is running: `curl http://localhost:8099/health`
  - `ADDON_URL` matches the addon port

**"Timeout waiting for addon"**
- Addon is taking longer to start (normal on first run)
- Increase `MAX_HEALTH_CHECKS` in `record_workflows.sh`
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

## Release Preparation

### Automated Release Preparation (Recommended)

Use the `prepare_release.sh` script to prepare a new release in one command:

```bash
# Single command to prepare release (version, GIFs, etc.)
./prepare_release.sh 1.4.8
```

This script will:
1. ✅ Validate version format (must be X.Y.Z)
2. ✅ Update version in config.yaml
3. ✅ Update version in Dockerfile
4. ✅ Update version in package.json
5. ✅ Record workflows (generates GIFs)
6. ✅ Verify all updates successful

**What NOT to do**: No test running is required during this process, as the main branch accepts only fully tested PRs.

### Manual Release Checklist

If you prefer manual control:

```bash
# 1. Update version manually in:
#    - squid_proxy_manager/config.yaml
#    - squid_proxy_manager/Dockerfile
#    - squid_proxy_manager/frontend/package.json

# 2. Record workflows (generates GIFs)
./record_workflows.sh

# 3. Verify GIFs in docs/gifs/
ls -lh ../docs/gifs/

# 4. Commit & push
git add ../docs/gifs/
git commit -m "release: prepare vX.Y.Z"
git push origin main
```

## Maintenance

Keep these files up-to-date:

- **record_workflows.sh** - Change if addon health check URL or Docker config changes
- **record_workflows_impl.py** - Change if UI workflows or steps change

All changes should be tested with:
```bash
./record_workflows.sh
```

---

**Last Updated**: January 2026
**Maintainer**: HA Squid Proxy Team
