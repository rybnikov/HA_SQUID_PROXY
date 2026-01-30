# Pre-Release Scripts

Scripts to prepare for releases of Squid Proxy Manager.

**IMPORTANT**: All development is Docker-first. Do NOT install tools locally. All workflows below run in Docker containers.

## Recording Workflows (Docker-Based)

Use Docker containers to capture user workflows as GIFs for documentation before releasing.

### Prerequisites

- Docker and Docker Compose installed (no local Playwright, ffmpeg, or Python required)
- Addon running locally: `./run_addon_local.sh start`

### Record Workflows as Videos → GIFs

The main workflow recording tool runs in Docker:

```bash
# Start the addon locally first
./run_addon_local.sh start

# In another terminal, record workflows using Docker
docker compose -f docker-compose.test.yaml \
  --profile e2e \
  run --rm e2e-runner \
  python /app/record_workflows.py http://addon:8099
```

**What it does**:
1. Runs Playwright inside `e2e-runner` Docker container (no local installation needed)
2. Records 5 workflow videos from the addon UI
3. Converts videos to animated GIFs using ffmpeg (also in container)
4. Outputs GIFs to `docs/gifs/` for use in README

**Workflows recorded**:
- `00-dashboard.gif` - Main dashboard overview
- `01-create-proxy.gif` - Creating a new proxy instance
- `02-manage-users.gif` - Adding users to a proxy
- `03-enable-https.gif` - Enabling HTTPS on an instance
- `04-view-logs.gif` - Viewing proxy logs

### Docker Container Used

The `e2e-runner` Docker image includes:
- Python 3.11
- Playwright browser automation
- ffmpeg for video/GIF conversion
- All dependencies pre-installed

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
   docker compose -f docker-compose.test.yaml \
     --profile e2e \
     run --rm e2e-runner \
     python /app/record_workflows.py http://addon:8099

   # GIFs saved to docs/gifs/
   ```

3. **Update version** in these files:
   - `squid_proxy_manager/config.yaml`
   - `squid_proxy_manager/Dockerfile`
   - `REQUIREMENTS.md` (release notes)

4. **Update README.md** with new GIFs:
   ```markdown
   ## Features in Action

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

### Docker Compose not found
Install Docker Desktop: https://www.docker.com/products/docker-desktop

### Addon not running
```bash
# Make sure addon is running first
./run_addon_local.sh start

# Verify it's up
docker ps | grep squid
```

### Recording fails
Check if `e2e-runner` Docker image is built:
```bash
docker compose -f docker-compose.test.yaml --profile e2e build e2e-runner
```

Then retry the recording command above.

## Docker-First Philosophy

✅ **All development is containerized:**
- No local Python installations needed
- No local Playwright or ffmpeg required
- All tools pre-installed in Docker images
- Consistent environment across machines

✅ **How to approach new tools:**
1. Install in Docker image (Dockerfile.test)
2. Add to requirements-test.txt
3. Build image: `docker compose build`
4. Run via Docker: `docker compose run`

❌ **Never install locally on macOS/Linux**
- Defeats the purpose of containerization
- Creates machine-specific issues
- Breaks for other developers
- Incompatible with CI/CD

## Images Used

| Image | Purpose | Location |
|-------|---------|----------|
| `e2e-runner` | Browser automation + GIF conversion | `tests/Dockerfile.test` |
| `addon` | Real squid-proxy-manager addon | `squid_proxy_manager/Dockerfile` |
| `test-runner` | Unit/integration tests | `tests/Dockerfile.test` |

All images include required tools pre-installed!
````
5. Monitor GitHub Actions for release build
