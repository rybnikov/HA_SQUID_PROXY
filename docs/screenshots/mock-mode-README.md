# Frontend Mock Mode Screenshots

**Note:** Screenshot images are **not** committed to the repository. They should be generated locally and attached to PRs via GitHub's interface for review purposes only.

## How to Generate Screenshots for PRs

### 1. Start Frontend in Mock Mode

```bash
# Start server in background
./run_frontend_for_agent.sh
```

### 2. Connect with Playwright MCP

```bash
# The server will be available at http://localhost:5173
# Use Playwright MCP tools to capture screenshots:

# Navigate to the dashboard
playwright-browser_navigate http://localhost:5173

# Wait for data to load
playwright-browser_wait_for 2

# Take dashboard screenshot
playwright-browser_take_screenshot mock-mode-dashboard.png

# Click settings on an instance
playwright-browser_click <settings-button>

# Take settings screenshot
playwright-browser_take_screenshot mock-mode-proxy-settings.png
```

### 3. Stop Server

```bash
./run_frontend_for_agent.sh --stop
```

### 4. Attach Screenshots to PR

Screenshots will be saved to `/tmp/playwright-logs/` by default. To attach them to a PR:

1. Navigate to your PR on GitHub
2. In the PR description or comments, drag and drop the screenshot files
3. GitHub will upload them and provide URLs
4. The screenshots will be visible in the PR for review

## What Screenshots Should Show

### Dashboard Screenshot
**Features to capture:**
- 3 pre-populated proxy instances
- Instance status indicators (Running/Stopped)
- Port and HTTPS configuration display
- User count for each instance
- Start/Stop/Settings controls

### Proxy Settings Screenshot
**Features to capture:**
- Proxy configuration modal
- Port configuration (e.g., 3128)
- HTTPS toggle state
- Instance status
- Delete and Save controls
- Tab navigation (Main, Users, Certificate, Logs, Test, Status)

## Mock Data

All mock data is defined in `squid_proxy_manager/frontend/src/api/mockData.ts`:
- 3 sample instances with different configurations
- User lists per instance
- Certificate information
- Sample logs

See [DEVELOPMENT.md](../../DEVELOPMENT.md#frontend-development-with-mock-mode) for full mock mode documentation.

## Why Screenshots Aren't Committed

- **Repository Size**: Binary image files bloat the repository over time
- **Version Control**: Images don't benefit from git's diff capabilities
- **Temporary Nature**: Screenshots are for PR review, not permanent documentation
- **GitHub Storage**: GitHub provides free hosting for PR attachments
- **Cleaner History**: Keeps the git history focused on code changes
