# Pre-Release Scripts

Scripts to prepare for releases of Squid Proxy Manager.

**IMPORTANT**: All development is Docker-first. Do NOT install tools locally. All workflows below run in Docker containers.

## Quick Start: Record Workflows

```bash
# 1. Start addon locally
./run_addon_local.sh start

# 2. Record workflows (automatic Docker execution)
cd pre_release_scripts
./record_workflows.sh http://addon:8099

# GIFs saved to docs/gifs/
```

## How It Works

### The Script (`record_workflows.sh`)

Runs **STRICTLY in Docker** - no local tools installed on your machine:

1. Checks Docker is running
2. Builds `e2e-runner` Docker image (if needed)
3. Executes workflow recording inside container
4. Outputs GIFs to `docs/gifs/`

**What gets recorded**:
- `00-dashboard.gif` - Main dashboard overview
- `01-create-proxy.gif` - Creating a new proxy instance
- `02-manage-users.gif` - Adding users to a proxy
- `03-enable-https.gif` - Enabling HTTPS on an instance
- `04-view-logs.gif` - Viewing proxy logs

### Docker Environment

The `e2e-runner` Docker image includes:
- Python 3.11
- Playwright browser automation
- ffmpeg for video/GIF conversion
- All dependencies pre-installed

No local installation needed!

## Release Process Checklist

Before releasing version X.Y.Z:

1. **Run full test suite** (Docker-based):
   ```bash
   ./run_tests.sh          # All tests
   ./run_tests.sh unit     # Fast suite
   ./run_tests.sh e2e      # E2E with real addon
   ```

2. **Record workflows** (Docker container):
   ```bash
   # Start addon locally
   ./run_addon_local.sh start

   # Record workflows using Docker (no local tools needed!)
   cd pre_release_scripts
   ./record_workflows.sh http://addon:8099

   # Stop addon when done
   ./run_addon_local.sh stop
   ```

3. **Update version** in these files:
   - `squid_proxy_manager/config.yaml`
   - `squid_proxy_manager/Dockerfile`
   - `REQUIREMENTS.md` (release notes)

4. **Update README.md** with new GIFs:
   ```markdown
   ## Features in Action

4. **Update README.md** with new GIFs:
   ```markdown
   ![Dashboard](docs/gifs/00-dashboard.gif)
   ![Create Proxy](docs/gifs/01-create-proxy.gif)
   ![Manage Users](docs/gifs/02-manage-users.gif)
   ![Enable HTTPS](docs/gifs/03-enable-https.gif)
   ![View Logs](docs/gifs/04-view-logs.gif)
   ```

5. **Commit & tag**:
   ```bash
   git add -A
   git commit -m "release: vX.Y.Z - [summary]"
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin main --tags
   ```

## Troubleshooting

### Docker not running
```bash
# Start Docker Desktop
# Then verify:
docker ps
```

### Addon not running
```bash
./run_addon_local.sh start
# Verify it's up
docker ps | grep squid
```

### Recording script fails
```bash
# Rebuild Docker image
docker compose -f docker-compose.test.yaml --profile e2e build e2e-runner

# Try again
./record_workflows.sh http://addon:8099
```

## Important: Docker-Only Development

This project uses **strict Docker-first development**:
- ✅ Do NOT install Playwright, ffmpeg, or any tools locally
- ✅ Do NOT run Python scripts locally
- ✅ Everything runs in Docker containers
- ✅ Refer to `.github/copilot-instructions.md` for full guidelines

````
5. Monitor GitHub Actions for release build
