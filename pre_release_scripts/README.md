# Pre-Release Scripts

Scripts to prepare for releases of Squid Proxy Manager.

## Recording Workflows

Use these scripts to capture user workflows as GIFs for documentation before releasing.

### Prerequisites

```bash
# Install dependencies
pip install playwright
python3 -m playwright install chromium

# Install ffmpeg (macOS)
brew install ffmpeg

# Or on Linux
sudo apt-get install ffmpeg
```

### Record Workflows as Videos → GIFs

The main workflow recording tool:

```bash
# Start the addon locally first
./run_addon_local.sh start

# In another terminal, record workflows
cd pre_release_scripts
./record_workflows.sh http://localhost:8099
```

**What it does**:
1. Records 5 workflow videos using Playwright (headless browser)
2. Converts each video to animated GIF using ffmpeg
3. Saves GIFs to `docs/gifs/` for use in README

**Workflows recorded**:
- `00-dashboard.gif` - Main dashboard overview
- `01-create-proxy.gif` - Creating a new proxy instance
- `02-manage-users.gif` - Adding users to a proxy
- `03-enable-https.gif` - Enabling HTTPS on an instance
- `04-view-logs.gif` - Viewing proxy logs

### Capture Screenshots Instead

If you prefer static screenshots instead of animated GIFs:

```bash
cd pre_release_scripts
python3 capture_workflows.py http://localhost:8099
```

**Output**:
- `docs/gifs/00_dashboard.png`
- `docs/gifs/01_create_instance_form.png`
- `docs/gifs/02_manage_users.png`
- `docs/gifs/03_https_settings.png`
- `docs/gifs/04_view_logs.png`

Convert to GIFs manually:
```bash
ffmpeg -i docs/gifs/00_dashboard.png -loop 0 docs/gifs/00_dashboard.gif
```

## Release Process Checklist

Before releasing version X.Y.Z:

1. **Test everything**:
   ```bash
   ./run_tests.sh
   ```

2. **Record workflows** (this folder):
   ```bash
   cd pre_release_scripts
   ./record_workflows.sh http://localhost:8099
   ```

3. **Update README.md** with new GIFs:
   ```markdown
   ## Features in Action

   ![Dashboard](docs/gifs/00-dashboard.gif)
   ![Create Proxy](docs/gifs/01-create-proxy.gif)
   ![Manage Users](docs/gifs/02-manage-users.gif)
   ![Enable HTTPS](docs/gifs/03-enable-https.gif)
   ![View Logs](docs/gifs/04-view-logs.gif)
   ```

4. **Update version** in 3 places:
   - `squid_proxy_manager/config.yaml`
   - `squid_proxy_manager/Dockerfile`
   - `REQUIREMENTS.md` (release notes)

5. **Commit & tag**:
   ```bash
   git add -A
   git commit -m "release: vX.Y.Z - [summary]"
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin main --tags
   ```

## Troubleshooting

### ffmpeg not found
```bash
brew install ffmpeg
```

### Playwright not installed
```bash
pip install playwright
python3 -m playwright install chromium
```

### Addon not running
```bash
# Make sure addon is running first
./run_addon_local.sh start

# Or run tests with real addon
./run_tests.sh e2e
```

### Videos not converting
Check if ffmpeg is working:
```bash
ffmpeg -version
```

If videos still won't convert, they're saved in `/tmp/playwright-videos` - convert manually:
```bash
ffmpeg -i /tmp/playwright-videos/video.webm \
  -vf 'fps=10,scale=640:-1:flags=lanczos' \
  -loop 0 docs/gifs/workflow.gif
```

## Next Steps

After recording workflows:
1. Review GIFs in `docs/gifs/`
2. Update README with GIF embeds
3. Commit and push
4. Tag release and push tags
5. Monitor GitHub Actions for release build
