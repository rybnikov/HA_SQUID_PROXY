# Feature Team Lead Memory

## Common Feature Patterns

### Adding a New Instance Feature
When adding features to proxy instances, typically involves:
1. Backend: New API endpoint in `main.py` + logic handler
2. Backend: Helper methods in `proxy_manager.py` or dedicated module
3. Frontend: New tab component in `frontend/src/features/instances/tabs/`
4. Frontend: Import/wire tab in `InstanceSettingsPage.tsx`
5. Frontend: API client method in `frontend/src/api/instances.ts`
6. Tests: Unit tests in `tests/unit/`, integration in `tests/integration/`, E2E in `tests/e2e/`
7. Version bump: 3 files (config.yaml, Dockerfile, package.json)

### Instance Metadata Storage (`instance.json`)
- Located at `/data/squid_proxy_manager/<instance_name>/instance.json`
- Core fields: `name`, `proxy_type`, `port`, `https_enabled`, `created_at`
- Optional fields: `forward_address`, `cover_domain`, `desired_state`
- Always validate instance names with `validate_instance_name()` before file operations
- Use `_safe_path()` helper for path construction to prevent traversal

### API Endpoint Patterns
- Handler functions: `async def handler_name(request)` in `main.py`
- Extract instance name: `name = _validated_name(request)`
- Check manager: `if manager is None: return web.json_response({"error": "..."}, status=503)`
- Success response: `web.json_response({"status": "...", ...})`
- Error responses: 400 (validation), 404 (not found), 500 (server error)
- Route registration: `app.router.add_<method>("/api/instances/{name}/<action>", handler)`

### Frontend Tab Component Pattern
```tsx
interface TabProps {
  instanceName: string;
  // other props
}

export function NewTab({ instanceName }: TabProps) {
  const [state, setState] = useState<Type>(...);
  const mutation = useMutation({ mutationFn: ..., onSuccess: ... });

  return (
    <div>
      {/* HA components with data-testid */}
      <HAButton data-testid="action-button">Action</HAButton>
    </div>
  );
}
```

### File Upload Handling
- Backend: Use `request.post()` to get multipart data, access via `data['fieldname']`
- Frontend: Use `<input type="file" />` or drag-drop area
- Validation: Check file extension, size limits, content type
- aiohttp body size limit: Set in `web.Application(client_max_size=bytes)`

## Architecture Constraints

### Proxy Types
- `squid`: HTTP/HTTPS proxy with auth, user management, certs
- `tls_tunnel`: Transparent nginx tunnel, no auth/users, forward address required

### Security Patterns
- All instance names MUST go through `validate_instance_name()` (prevents path traversal)
- Use `_safe_path()` for all path construction under `/data/squid_proxy_manager/`
- No `ssl_bump` directive in Squid HTTPS configs (causes fatal errors)
- htpasswd files are per-instance: `/data/squid_proxy_manager/<name>/passwd`

### Testing Requirements
- E2E tests require `data-testid` attributes on all interactive elements
- Format: `data-testid="feature-action-button"` (kebab-case)
- Tests run in Docker, no local Python venv needed
- All tests must pass before merge (enforced by CI)

## Known Issues & Solutions

### HA Ingress Limitations
- **ALL blocking dialogs blocked**: `window.alert()`, `window.confirm()`, `window.prompt()` → use inline feedback states or custom `<HADialog>` modals
- Service Worker caching → unregister SW + clear cache storage for frontend updates
- iframe restrictions → check cross-origin requirements
- **Critical**: Always check `.claude/agents/` memory files for HA-specific constraints before planning

### Docker Build Gotchas
- `docker compose restart` does NOT rebuild
- Use `--no-cache` when `COPY rootfs/` changes aren't picked up
- Correct rebuild: `docker compose build --no-cache addon && docker compose up -d`

## Version Management
Version must be updated in 3 files:
1. `/Users/rbnkv/Projects/HA_SQUID_PROXY/squid_proxy_manager/config.yaml` → `version: "X.Y.Z"`
2. `/Users/rbnkv/Projects/HA_SQUID_PROXY/squid_proxy_manager/Dockerfile` → `io.hass.version="X.Y.Z"`
3. `/Users/rbnkv/Projects/HA_SQUID_PROXY/squid_proxy_manager/frontend/package.json` → `"version": "X.Y.Z"`

## File Locations Reference
- Backend app: `/Users/rbnkv/Projects/HA_SQUID_PROXY/squid_proxy_manager/rootfs/app/`
- Frontend: `/Users/rbnkv/Projects/HA_SQUID_PROXY/squid_proxy_manager/frontend/`
- Tests: `/Users/rbnkv/Projects/HA_SQUID_PROXY/tests/`
- Data dir (runtime): `/data/squid_proxy_manager/`
