# Frontend Mock Mode Implementation

## Overview

This implementation provides a complete frontend mock mode system that enables the coding agent and sub-agents to work independently of the backend. The frontend can now run with simulated data, allowing for rapid UI development, testing, and validation.

## Quick Start

### For Interactive Development
```bash
./run_frontend_mock.sh              # Starts on port 5173
./run_frontend_mock.sh --port 8080  # Custom port
./run_frontend_mock.sh --host       # Expose on network
```

### For Agent/Automation
```bash
./run_frontend_for_agent.sh         # Start in background
# → http://localhost:5173 is ready for Playwright
./run_frontend_for_agent.sh --stop  # Stop when done
```

## Architecture

### Environment-Based Switching
- **Environment Variable**: `VITE_MOCK_MODE=true`
- **Detection**: Checked at module import time in `api/instances.ts` and `api/status.ts`
- **Fallback**: Real API calls when not in mock mode

### Mock Data Provider
**Location**: `squid_proxy_manager/frontend/src/api/mockData.ts`

**Features**:
- 3 pre-configured proxy instances with different states
- Full API coverage (instances, users, certificates, logs, testing)
- Simulated network latency (300ms)
- Stateful operations within session
- Realistic error scenarios

**Mock Instances**:
1. **production-proxy**
   - Port: 3128
   - HTTPS: Enabled
   - Users: 3 (admin, user1, user2)
   - Status: Running

2. **development-proxy**
   - Port: 3129
   - HTTPS: Disabled
   - Users: 1 (developer)
   - Status: Running

3. **staging-proxy**
   - Port: 3130
   - HTTPS: Enabled
   - Users: 2 (tester1, tester2)
   - Status: Stopped

## API Coverage

All API endpoints are mocked:

| Endpoint | Mock Support | Notes |
|----------|--------------|-------|
| `GET /api/instances` | ✅ | Returns 3 mock instances |
| `POST /api/instances` | ✅ | Creates new instance (in-memory) |
| `POST /api/instances/:name/start` | ✅ | Changes status to running |
| `POST /api/instances/:name/stop` | ✅ | Changes status to stopped |
| `DELETE /api/instances/:name` | ✅ | Removes instance (in-memory) |
| `PATCH /api/instances/:name` | ✅ | Updates port/HTTPS |
| `GET /api/instances/:name/users` | ✅ | Returns user list |
| `POST /api/instances/:name/users` | ✅ | Adds user |
| `DELETE /api/instances/:name/users/:user` | ✅ | Removes user |
| `GET /api/instances/:name/logs` | ✅ | Returns sample logs |
| `POST /api/instances/:name/logs/clear` | ✅ | Simulates clearing |
| `GET /api/instances/:name/certs` | ✅ | Returns cert info |
| `POST /api/instances/:name/certs` | ✅ | Regenerates cert |
| `POST /api/instances/:name/test` | ✅ | Simulates connectivity test |
| `GET /` (status) | ✅ | Returns healthy status |

## Scripts

### `run_frontend_mock.sh`
**Purpose**: Interactive development with hot reload

**Features**:
- Starts Vite dev server in foreground
- Hot module replacement (HMR) enabled
- Suitable for active development work
- Ctrl+C to stop

**Usage**:
```bash
./run_frontend_mock.sh              # Default: localhost:5173
./run_frontend_mock.sh --port 3000  # Custom port
./run_frontend_mock.sh --host       # Expose on 0.0.0.0
```

### `run_frontend_for_agent.sh`
**Purpose**: Background server for automation/agents

**Features**:
- Starts server in background
- PID saved to `/tmp/frontend_mock_server.pid`
- Health check with timeout (30s)
- Logs to `/tmp/frontend_mock_server.log`
- Playwright-ready

**Usage**:
```bash
# Start server
./run_frontend_for_agent.sh
# → Server starts at http://localhost:5173
# → PID saved, logs available

# Use Playwright to interact
# (navigate, click, screenshot, etc.)

# Stop server
./run_frontend_for_agent.sh --stop
```

## Playwright MCP Workflow

### Example: Capture Proxy Settings Screenshot

```bash
# 1. Start frontend server
./run_frontend_for_agent.sh

# 2. Use Playwright MCP tools
playwright-browser_navigate http://localhost:5173
playwright-browser_wait_for 2  # Wait for data to load
playwright-browser_click <settings-button>
playwright-browser_take_screenshot proxy-settings.png

# 3. Stop server
./run_frontend_for_agent.sh --stop
```

### Attaching Screenshots to PRs

Screenshots are saved to `/tmp/playwright-logs/` by default. To attach them to a PR:

1. **Generate screenshots** using the workflow above
2. **Locate screenshots** in `/tmp/playwright-logs/` or your specified output directory
3. **Navigate to your PR** on GitHub
4. **Drag and drop** screenshot files into the PR description or comment box
5. **GitHub will upload** the images and provide markdown URLs automatically
6. **Preview** the PR to ensure screenshots are visible

**Example:**
```bash
# After taking screenshots with Playwright
ls /tmp/playwright-logs/
# → proxy-settings.png, dashboard.png

# Copy to an accessible location if needed
cp /tmp/playwright-logs/*.png ~/screenshots-for-pr/

# Then drag and drop these files into the GitHub PR interface
```

**Benefits of GitHub-hosted screenshots:**
- No repository bloat from binary files
- Automatic hosting by GitHub
- Easy to update by commenting with new screenshots
- Clean git history without image file changes

### Example: Validate UI Elements

```bash
# Start server
./run_frontend_for_agent.sh

# Use Playwright to validate
# - Check instance count (should be 3)
# - Verify running status indicators
# - Test button states (enabled/disabled)
# - Validate modal opens correctly

# Stop server
./run_frontend_for_agent.sh --stop
```

## Testing

### Frontend Unit Tests
**Location**: `squid_proxy_manager/frontend/src/tests/mockMode.test.ts`

**Coverage**:
- Mock instance retrieval
- Instance creation
- Start/stop operations
- User management
- Certificate info

**Run**:
```bash
cd squid_proxy_manager/frontend
npm test
```

### Integration with Existing Tests
Mock mode tests are included in the standard frontend test suite:
```bash
cd squid_proxy_manager/frontend
npm run typecheck  # Type checking
npm run lint       # Linting
npm test           # All tests (includes mock mode)
```

## Development Workflow

### UI Component Development
1. Start mock mode: `./run_frontend_mock.sh`
2. Open browser: http://localhost:5173
3. Make UI changes (HMR updates automatically)
4. Test with mock data (no backend needed)
5. Capture screenshots when ready

### Agent Validation
1. Start background server: `./run_frontend_for_agent.sh`
2. Connect with Playwright MCP
3. Navigate and interact with UI
4. Capture validation screenshots
5. Stop server: `./run_frontend_for_agent.sh --stop`

### Before Committing
```bash
cd squid_proxy_manager/frontend
npm run typecheck && npm run lint && npm test
# All should pass
```

## Documentation

### Main Documentation
- **DEVELOPMENT.md**: Full mock mode section added with:
  - Quick start commands
  - Mock data structure
  - Use cases
  - Playwright integration
  - Troubleshooting

### Screenshot Documentation
- **docs/screenshots/mock-mode-README.md**: Guide for generating screenshots:
  - How to capture screenshots using Playwright
  - How to attach screenshots to PRs via GitHub
  - What features to capture
  - Mock data reference

**Note:** Screenshot images are not committed to the repository. They should be generated locally and attached to PRs via GitHub's interface.

## Files Modified/Added

### New Files
- `squid_proxy_manager/frontend/src/api/mockData.ts` (250 lines)
- `squid_proxy_manager/frontend/src/tests/mockMode.test.ts` (110 lines)
- `run_frontend_mock.sh` (50 lines)
- `run_frontend_for_agent.sh` (110 lines)
- `docs/screenshots/mock-mode-README.md` (screenshot generation guide)

### Modified Files
- `squid_proxy_manager/frontend/src/api/instances.ts` - Added mock mode checks
- `squid_proxy_manager/frontend/src/api/status.ts` - Added mock mode checks
- `squid_proxy_manager/frontend/package.json` - Added `dev:mock` script
- `squid_proxy_manager/frontend/index.html` - Fixed token handling
- `squid_proxy_manager/frontend/src/types/vite-env.d.ts` - Added types
- `DEVELOPMENT.md` - Added comprehensive section

## Benefits

1. **Faster Development**: No backend startup required
2. **Consistent Testing**: Same mock data every time
3. **Agent Autonomy**: Sub-agents can validate independently
4. **Offline Work**: No network dependencies
5. **Screenshot Automation**: Easy to capture for PRs
6. **Rapid Iteration**: HMR for instant feedback

## Limitations

- Mock data resets on server restart (no persistence)
- No real Squid proxy functionality (just UI simulation)
- Certificate operations are simulated (no real TLS)
- Logs are static samples (not generated)

## Future Enhancements

Potential improvements:
- Local storage persistence for mock data
- Configurable mock data via JSON file
- Mock data generator for custom scenarios
- Network error simulation
- Slow connection simulation
- Mock data import/export

## Troubleshooting

### Port Already in Use
```bash
# Check what's using port 5173
lsof -i :5173

# Use different port
./run_frontend_mock.sh --port 8080
```

### Server Won't Start
```bash
# Check logs
cat /tmp/frontend_mock_server.log

# Install dependencies
cd squid_proxy_manager/frontend
npm install
```

### Mock Data Not Loading
1. Check browser console for errors
2. Verify `VITE_MOCK_MODE=true` is set
3. Hard refresh browser (Ctrl+Shift+R)

### Playwright Can't Connect
```bash
# Verify server is running
curl http://localhost:5173

# Check PID file exists
cat /tmp/frontend_mock_server.pid

# Restart server
./run_frontend_for_agent.sh --stop
./run_frontend_for_agent.sh
```

## Conclusion

This implementation fully satisfies the requirements:

✅ **Requirement 1**: Frontend runs with mock data without backend
✅ **Requirement 2**: Sub-agent can capture screenshots via Playwright
✅ **Requirement 3**: All development guardrails respected (tests pass)

The coding agent and sub-agents can now work independently on frontend features, validate changes, and capture screenshots without backend dependencies.
