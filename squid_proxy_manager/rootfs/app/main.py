#!/usr/bin/env python3
"""Main entry point for Squid Proxy Manager add-on."""
# Very early logging setup to catch any startup issues
import os
import sys

# Set up basic logging immediately, before any other imports
try:
    import logging

    LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,  # Force reconfiguration if logging was already set up
    )
    _EARLY_LOGGER = logging.getLogger(__name__)
    _EARLY_LOGGER.info("=" * 60)
    _EARLY_LOGGER.info("Python script started - initializing...")
    _EARLY_LOGGER.info("Python version: %s", sys.version)
    _EARLY_LOGGER.info("Python executable: %s", sys.executable)
    _EARLY_LOGGER.info("Working directory: %s", os.getcwd())
    _EARLY_LOGGER.info("=" * 60)
except Exception as e:
    print(f"CRITICAL: Failed to set up logging: {e}", file=sys.stderr)
    sys.exit(1)

# Harden default permissions for new files
os.umask(0o077)

# Now do other imports with error handling
try:
    import asyncio
    import json
    from pathlib import Path

    _EARLY_LOGGER.info("Core imports successful")
except Exception as e:
    _EARLY_LOGGER.critical("Failed to import core modules: %s", e, exc_info=True)
    sys.exit(1)

try:
    import aiohttp
    from aiohttp import web
    from aiolimiter import AsyncLimiter

    _EARLY_LOGGER.info("aiohttp imports successful")
except Exception as e:
    _EARLY_LOGGER.critical("Failed to import aiohttp: %s", e, exc_info=True)
    sys.exit(1)

# Add app directory to path
sys.path.insert(0, "/app")
_EARLY_LOGGER.info("Added /app to Python path")

try:
    from proxy_manager import ProxyInstanceManager

    _EARLY_LOGGER.info("proxy_manager import successful")
except Exception as e:
    _EARLY_LOGGER.critical("Failed to import proxy_manager: %s", e, exc_info=True)
    sys.exit(1)

# Now use the logger normally
_LOGGER = _EARLY_LOGGER
_LOGGER.info("All imports completed successfully")

# Paths
APP_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = Path("/data/options.json")
HA_API_URL = os.getenv("SUPERVISOR", "http://supervisor")
HA_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")
APP_VERSION = "1.4.4"
STATIC_ROOT = Path("/app/static")
INDEX_HTML = STATIC_ROOT / "index.html"
ASSETS_DIR = STATIC_ROOT / "assets"
DEV_FRONTEND_ROOT = APP_ROOT.parent.parent / "frontend"
DEV_INDEX_HTML = DEV_FRONTEND_ROOT / "index.html"
ALLOWED_ORIGINS = {
    "http://localhost:8123",
    "http://homeassistant.local:8123",
}
API_LIMITER = AsyncLimiter(120, 60)
API_REQUEST_TIMEOUT = 30

# Manager will be initialized in main()
manager = None


# Middlewares
@web.middleware
async def normalize_path_middleware(request, handler):
    """Normalize multiple slashes in path for ingress compatibility."""
    import re

    original_path = request.path
    normalized_path = re.sub(r"/+", "/", original_path)

    if normalized_path != original_path:
        _LOGGER.debug("Normalizing path: %s -> %s", original_path, normalized_path)

        # If the original request didn't match any route (handler is 404)
        # but the normalized path DOES match a route, we should use that instead.
        # This is common with ingress adding extra slashes.
        try:
            # Re-resolve the path
            cloned_request = request.clone(rel_url=request.rel_url.with_path(normalized_path))
            match_info = await request.app.router.resolve(cloned_request)

            if match_info.http_exception is None:
                # We found a better match!
                # IMPORTANT: We must use the match_info handler and ensure the request
                # passed to it has the correct match_info attached.
                # In aiohttp, request.match_info is a property that accesses _match_info.
                # We need to set it on the cloned request.
                # Using setattr because it's technically a private attribute.
                cloned_request._match_info = match_info
                return await match_info.handler(cloned_request)
        except Exception as ex:
            # Fallback to original handler if anything goes wrong
            _LOGGER.debug(
                "Path normalization failed for %s -> %s: %s",
                original_path,
                normalized_path,
                ex,
            )

        # If we didn't find a better match, but it's just the root, handle it
        if normalized_path == "/":
            return await root_handler(request)

    return await handler(request)


@web.middleware
async def logging_middleware(request, handler):
    """Log requests and responses with status-based levels."""
    # Log all requests at DEBUG, but log errors at INFO/ERROR
    _LOGGER.debug("Request: %s %s from %s", request.method, request.path_qs, request.remote)
    try:
        response = await handler(request)
        if response.status >= 400:
            _LOGGER.info("Response: %s %s -> %d", request.method, request.path_qs, response.status)
        else:
            _LOGGER.debug("Response: %s %s -> %d", request.method, request.path_qs, response.status)
        return response
    except web.HTTPException as ex:
        # Handle known HTTP exceptions (like 404) without logging a full traceback
        if ex.status >= 400:
            _LOGGER.info("Response: %s %s -> %d", request.method, request.path_qs, ex.status)
        raise
    except Exception as ex:
        _LOGGER.error(
            "Unhandled exception in handler for %s %s: %s",
            request.method,
            request.path_qs,
            ex,
            exc_info=True,
        )
        raise


@web.middleware
async def auth_middleware(request, handler):
    """Bearer token auth for API endpoints."""
    if request.path.startswith("/api/"):
        if request.method == "OPTIONS":
            return await handler(request)
        if not HA_TOKEN:
            return web.json_response({"error": "Supervisor token not configured"}, status=503)
        auth_header = request.headers.get("Authorization", "")
        expected = f"Bearer {HA_TOKEN}"
        if auth_header != expected:
            cookie_token = request.cookies.get("SUPERVISOR_TOKEN", "")
            if cookie_token != HA_TOKEN:
                return web.json_response({"error": "Unauthorized"}, status=401)
    return await handler(request)


@web.middleware
async def rate_limit_middleware(request, handler):
    """Basic rate limiting for API endpoints."""
    if request.path.startswith("/api/"):
        async with API_LIMITER:
            return await handler(request)
    return await handler(request)


@web.middleware
async def timeout_middleware(request, handler):
    """Timeout protection for API endpoints."""
    if request.path.startswith("/api/"):
        try:
            return await asyncio.wait_for(handler(request), timeout=API_REQUEST_TIMEOUT)
        except asyncio.TimeoutError:
            return web.json_response({"error": "Request timeout"}, status=504)
    return await handler(request)


@web.middleware
async def cors_middleware(request, handler):
    """CORS headers for HA ingress origins."""
    if request.method == "OPTIONS":
        response = web.Response(status=200)
    else:
        response = await handler(request)

    origin = request.headers.get("Origin")
    if origin and origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Vary"] = "Origin"
    return response


@web.middleware
async def security_headers_middleware(request, handler):
    """Add security headers to responses."""
    response = await handler(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


async def get_config():
    """Load add-on configuration."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def get_ingress_port():
    """Get ingress port - using fixed port 8099.

    Using a fixed port (8099) configured in config.yaml for reliability.
    Dynamic port discovery with ingress_port: 0 proved unreliable.
    """
    # Use fixed port 8099 as configured in config.yaml
    port = 8099
    _LOGGER.info("Using fixed ingress port: %d (from config.yaml)", port)
    return port


async def root_handler(request):
    """Root endpoint for ingress - serves web UI or JSON."""
    _LOGGER.debug("Root handler called from %s", request.remote)

    # Check if client wants HTML (web UI)
    accept_header = request.headers.get("Accept", "")
    if "text/html" in accept_header:
        return await web_ui_handler(request)

    # Return JSON for API clients
    response_data = {
        "status": "ok",
        "service": "squid_proxy_manager",
        "version": APP_VERSION,
        "api": "/api",
        "manager_initialized": manager is not None,
    }
    _LOGGER.info("Root endpoint accessed - manager initialized: %s", manager is not None)
    return web.json_response(response_data)


def _load_index_html() -> str | None:
    """Load the SPA index.html from the built assets or dev frontend."""
    index_path = (
        INDEX_HTML if INDEX_HTML.exists() else DEV_INDEX_HTML if DEV_INDEX_HTML.exists() else None
    )
    if not index_path:
        return None
    return index_path.read_text(encoding="utf-8")


async def web_ui_handler(request):
    """Serve web UI HTML page."""
    html_content = _load_index_html()
    if html_content is None:
        return web.Response(
            text="UI build not found. Please build the frontend assets.",
            status=503,
            content_type="text/plain",
        )

    html_content = html_content.replace("__SUPERVISOR_TOKEN_VALUE__", json.dumps(HA_TOKEN)).replace(
        "__APP_VERSION_VALUE__", json.dumps(APP_VERSION)
    )
    response = web.Response(text=html_content, content_type="text/html")
    if HA_TOKEN:
        response.set_cookie("SUPERVISOR_TOKEN", HA_TOKEN, httponly=True, samesite="Lax")
    return response


async def spa_fallback_handler(request):
    """Fallback to index.html for SPA routes."""
    accept_header = request.headers.get("Accept", "")
    if "text/html" in accept_header or "application/xhtml+xml" in accept_header:
        return await web_ui_handler(request)
    raise web.HTTPNotFound()


async def health_check(request):
    """Health check endpoint."""
    _LOGGER.debug("Health check called from %s", request.remote)
    health_status = {
        "status": "ok",
        "service": "squid_proxy_manager",
        "manager_initialized": manager is not None,
        "version": APP_VERSION,
    }
    _LOGGER.info(
        "Health check - status: ok, manager: %s", "initialized" if manager else "not initialized"
    )
    return web.json_response(health_status)


async def get_instances(request):
    """Get list of proxy instances."""
    _LOGGER.debug("GET /api/instances called from %s", request.remote)
    if manager is None:
        _LOGGER.warning("GET /api/instances called but manager is not initialized")
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        _LOGGER.info("Retrieving list of proxy instances")
        instances = await manager.get_instances()
        _LOGGER.info("Retrieved %d proxy instances", len(instances))
        return web.json_response({"instances": instances, "count": len(instances)})
    except Exception as ex:
        _LOGGER.error("Failed to get instances: %s", ex, exc_info=True)
        return web.json_response({"error": str(ex)}, status=500)


async def create_instance(request):
    """Create a new proxy instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        data = await request.json()
        name = data.get("name")
        port = data.get("port", 3128)
        https_enabled = data.get("https_enabled", False)
        users = data.get("users", [])
        cert_params = data.get("cert_params")  # Certificate parameters

        if not name:
            return web.json_response({"error": "Instance name is required"}, status=400)

        instance = await manager.create_instance(
            name=name,
            port=port,
            https_enabled=https_enabled,
            users=users,
            cert_params=cert_params,
        )

        return web.json_response({"status": "created", "instance": instance}, status=201)
    except ValueError as ex:
        _LOGGER.warning("Validation error creating instance: %s", ex)
        return web.json_response({"error": str(ex)}, status=400)
    except Exception as ex:
        _LOGGER.error("Failed to create instance: %s", ex)
        return web.json_response({"error": str(ex)}, status=500)


async def start_instance(request):
    """Start a proxy instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        if not name:
            return web.json_response({"error": "Instance name is required"}, status=400)

        success = await manager.start_instance(name)
        if success:
            return web.json_response({"status": "started", "instance": name})
        else:
            return web.json_response({"error": "Failed to start instance"}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to start instance: %s", ex)
        return web.json_response({"error": str(ex)}, status=500)


async def stop_instance(request):
    """Stop a proxy instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        if not name:
            return web.json_response({"error": "Instance name is required"}, status=400)

        # Verify instance exists
        instances = await manager.get_instances()
        if not any(i["name"] == name for i in instances):
            return web.json_response({"error": f"Instance {name} not found"}, status=404)

        success = await manager.stop_instance(name)
        if success:
            return web.json_response({"status": "stopped", "instance": name})
        else:
            return web.json_response({"error": "Failed to stop instance"}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to stop instance %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def remove_instance(request):
    """Remove a proxy instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        if not name:
            return web.json_response({"error": "Instance name is required"}, status=400)

        # Check if instance exists first
        instances = await manager.get_instances()
        if not any(i["name"] == name for i in instances):
            return web.json_response({"error": f"Instance '{name}' not found"}, status=404)

        success = await manager.remove_instance(name)
        if success:
            _LOGGER.info("✓ Instance '%s' removed successfully", name)
            return web.json_response({"status": "removed", "instance": name})
        else:
            return web.json_response({"error": "Failed to remove instance"}, status=500)
    except ValueError as ex:
        _LOGGER.warning("Validation error removing instance %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=400)
    except Exception as ex:
        _LOGGER.error("Failed to remove instance %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def get_instance_users(request):
    """Get users for an instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        users = await manager.get_users(name)
        return web.json_response({"users": [{"username": u} for u in users]})
    except ValueError as ex:
        _LOGGER.warning("Validation error getting users for %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=400)
    except Exception as ex:
        _LOGGER.error("Failed to get users for %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def add_instance_user(request):
    """Add a user to an instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        data = await request.json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return web.json_response({"error": "Username and password are required"}, status=400)

        success = await manager.add_user(name, username, password)
        if success:
            return web.json_response({"status": "user_added"})
        return web.json_response({"error": "Failed to add user"}, status=500)
    except ValueError as ex:
        _LOGGER.warning("Validation error adding user to %s: %s", name, ex)
        status = 409 if "already exists" in str(ex).lower() else 400
        return web.json_response({"error": str(ex)}, status=status)
    except Exception as ex:
        _LOGGER.error("Failed to add user to %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def remove_instance_user(request):
    """Remove a user from an instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        username = request.match_info.get("username")

        if not username:
            return web.json_response({"error": "Username is required"}, status=400)

        success = await manager.remove_user(name, username)
        if success:
            return web.json_response({"status": "user_removed"})
        return web.json_response({"error": "Failed to remove user"}, status=500)
    except ValueError as ex:
        _LOGGER.warning("Validation error removing user from %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=400)
    except Exception as ex:
        _LOGGER.error("Failed to remove user from %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def get_instance_logs(request):
    """Get logs for an instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        log_type = request.query.get("type", "cache")  # 'cache' or 'access'

        from proxy_manager import LOGS_DIR

        log_file = LOGS_DIR / name / f"{log_type}.log"

        if not log_file.exists():
            return web.Response(text=f"Log file {log_type}.log not found.")

        # Return last 100 lines
        with open(log_file) as f:
            lines = f.readlines()
            return web.Response(text="".join(lines[-100:]))
    except Exception as ex:
        _LOGGER.error("Failed to get logs for %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def clear_instance_logs(request):
    """Clear logs for an instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        log_type = request.query.get("type", "access")

        if log_type not in ("access", "cache"):
            return web.json_response({"error": "Invalid log type"}, status=400)

        from proxy_manager import LOGS_DIR

        log_file = LOGS_DIR / name / f"{log_type}.log"
        if not log_file.exists():
            return web.json_response(
                {"status": "cleared", "message": "Log file not found"}, status=200
            )

        log_file.write_text("")
        return web.json_response({"status": "cleared"})
    except Exception as ex:
        _LOGGER.error("Failed to clear logs for %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def get_instance_certificate_info(request):
    """Get certificate details for an instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        from proxy_manager import CERTS_DIR

        cert_file = CERTS_DIR / name / "squid.crt"
        if not cert_file.exists():
            return web.json_response(
                {"status": "missing", "message": "Certificate not found"}, status=404
            )

        cert_pem = cert_file.read_text()

        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID

            cert = x509.load_pem_x509_certificate(cert_file.read_bytes())
            common_name = None
            try:
                cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                common_name = cn[0].value if cn else None
            except Exception:
                common_name = None

            if hasattr(cert, "not_valid_before_utc"):
                not_valid_before = cert.not_valid_before_utc
            else:
                not_valid_before = cert.not_valid_before

            if hasattr(cert, "not_valid_after_utc"):
                not_valid_after = cert.not_valid_after_utc
            else:
                not_valid_after = cert.not_valid_after

            return web.json_response(
                {
                    "status": "valid",
                    "common_name": common_name,
                    "not_valid_before": not_valid_before.isoformat() if not_valid_before else None,
                    "not_valid_after": not_valid_after.isoformat() if not_valid_after else None,
                    "pem": cert_pem,
                }
            )
        except Exception as ex:
            _LOGGER.error("Failed to parse certificate for %s: %s", name, ex)
            return web.json_response(
                {"status": "invalid", "error": str(ex), "pem": cert_pem}, status=200
            )
    except Exception as ex:
        _LOGGER.error("Failed to read certificate info for %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def update_instance_settings(request):
    """Update instance settings."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        data = await request.json()
        port = data.get("port")
        https_enabled = data.get("https_enabled")
        cert_params = data.get("cert_params")  # Certificate parameters

        success = await manager.update_instance(
            name,
            port,
            https_enabled,
            cert_params=cert_params,
        )
        if success:
            return web.json_response({"status": "updated"})
        return web.json_response({"error": "Failed to update settings"}, status=500)
    except ValueError as ex:
        _LOGGER.warning("Validation error updating instance %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=400)
    except Exception as ex:
        _LOGGER.error("Failed to update settings for %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def regenerate_instance_certs(request):
    """Regenerate certificates for an instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        data = await request.json() if request.content_length else {}
        cert_params = data.get("cert_params")
        success = await manager.regenerate_certs(name, cert_params=cert_params)
        if success:
            return web.json_response({"status": "certs_regenerated"})
        return web.json_response({"error": "Failed to regenerate certificates"}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to regenerate certificates for %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def test_instance_connectivity(request):
    """Test proxy instance connectivity."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        target_url = data.get("target_url")

        if not username or not password:
            return web.json_response({"error": "Username and password are required"}, status=400)

        # Get instance details
        instances = await manager.get_instances()
        instance = next((i for i in instances if i["name"] == name), None)
        if not instance:
            return web.json_response({"error": "Instance not found"}, status=404)

        if not instance.get("running", False):
            return web.json_response({"error": "Instance is not running"}, status=400)

        # Test connectivity using subprocess curl
        import subprocess  # nosec B404

        https_enabled = instance.get("https_enabled", False)
        protocol = "https" if https_enabled else "http"
        proxy_url = f"{protocol}://{username}:{password}@localhost:{instance['port']}"
        default_target = "https://www.google.com" if https_enabled else "http://www.google.com"
        target_url = target_url or default_target

        try:
            curl_args = [
                "curl",
                "-x",
                proxy_url,
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                target_url,
                "--max-time",
                "10",
                "--connect-timeout",
                "5",
            ]
            if https_enabled:
                curl_args.insert(3, "--proxy-insecure")

            result = subprocess.run(  # nosec B603,B607
                curl_args,
                capture_output=True,
                text=True,
                timeout=15,
            )

            success = result.returncode == 0 and result.stdout.strip() in [
                "200",
                "301",
                "302",
                "307",
            ]

            return web.json_response(
                {
                    "status": "success" if success else "failed",
                    "http_code": result.stdout.strip() if result.returncode == 0 else None,
                    "error": result.stderr if not success and result.stderr else None,
                    "message": f"Connection {'succeeded' if success else 'failed'}",
                }
            )
        except subprocess.TimeoutExpired:
            return web.json_response(
                {"status": "failed", "error": "Connection timeout"}, status=500
            )
        except Exception as curl_ex:
            _LOGGER.error("Curl test failed: %s", curl_ex)
            return web.json_response({"status": "failed", "error": str(curl_ex)}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to test connectivity: %s", ex)
        return web.json_response({"error": str(ex)}, status=500)


async def start_app():
    """Start the web application."""
    _LOGGER.info("Initializing web application...")
    app = web.Application(client_max_size=1_048_576)

    app.middlewares.append(normalize_path_middleware)
    app.middlewares.append(logging_middleware)
    app.middlewares.append(auth_middleware)
    app.middlewares.append(rate_limit_middleware)
    app.middlewares.append(timeout_middleware)
    app.middlewares.append(cors_middleware)
    app.middlewares.append(security_headers_middleware)

    # Root and health routes (for ingress health checks)
    # With ingress_entry: /, all routes are accessible directly
    _LOGGER.info("Registering routes...")
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_check)

    # API routes
    app.router.add_get("/api/instances", get_instances)
    app.router.add_post("/api/instances", create_instance)
    app.router.add_patch("/api/instances/{name}", update_instance_settings)
    app.router.add_post("/api/instances/{name}/start", start_instance)
    app.router.add_post("/api/instances/{name}/stop", stop_instance)
    app.router.add_delete("/api/instances/{name}", remove_instance)
    app.router.add_post("/api/instances/{name}/certs", regenerate_instance_certs)
    app.router.add_get("/api/instances/{name}/certs", get_instance_certificate_info)
    app.router.add_get("/api/instances/{name}/logs", get_instance_logs)
    app.router.add_post("/api/instances/{name}/logs/clear", clear_instance_logs)

    # User management API
    app.router.add_get("/api/instances/{name}/users", get_instance_users)
    app.router.add_post("/api/instances/{name}/users", add_instance_user)
    app.router.add_delete("/api/instances/{name}/users/{username}", remove_instance_user)
    app.router.add_post("/api/instances/{name}/test", test_instance_connectivity)

    if ASSETS_DIR.exists():
        app.router.add_static("/assets/", ASSETS_DIR, name="assets")

    # SPA fallback for deep links (ingress-safe)
    app.router.add_get("/{tail:.*}", spa_fallback_handler)

    _LOGGER.info("Routes registered: / (web UI), /health, /api/instances")

    _LOGGER.info("Setting up AppRunner...")
    runner = web.AppRunner(app)
    await runner.setup()
    _LOGGER.info("AppRunner setup complete")

    # Use fixed ingress port (8099) as configured in config.yaml
    _LOGGER.info("Determining ingress port...")
    port = get_ingress_port()
    _LOGGER.info("Starting TCP site on 0.0.0.0:%d...", port)

    try:
        site = web.TCPSite(runner, "0.0.0.0", port)  # nosec B104
        await site.start()
        _LOGGER.info("✓ TCP site started successfully on port %d", port)

        # Give the server a moment to fully bind
        await asyncio.sleep(0.5)

        # Verify server is responding to HTTP requests (what ingress will actually do)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://127.0.0.1:{port}/health", timeout=aiohttp.ClientTimeout(total=2)
                ) as response:
                    if response.status == 200:
                        _LOGGER.info("✓ Verified HTTP server is responding on port %d", port)
                    else:
                        _LOGGER.warning(
                            "⚠ HTTP server responded with status %d on port %d",
                            response.status,
                            port,
                        )
        except Exception as ex:
            _LOGGER.warning("⚠ Could not verify HTTP server is responding on port %d: %s", port, ex)
    except OSError as ex:
        _LOGGER.error("✗ Failed to start TCP site on port %d: %s", port, ex, exc_info=True)
        raise
    except Exception as ex:
        _LOGGER.error("✗ Unexpected error starting TCP site: %s", ex, exc_info=True)
        raise

    _LOGGER.info("=" * 60)
    _LOGGER.info("✓ Squid Proxy Manager API started successfully")
    _LOGGER.info("  Listening on: 0.0.0.0:%d", port)
    _LOGGER.info(
        "  Ingress URL: http://supervisor/ingress/%s",
        (
            os.getenv("SUPERVISOR_TOKEN", "unknown")[:8]
            if os.getenv("SUPERVISOR_TOKEN")
            else "unknown"
        ),
    )
    _LOGGER.info("  Server is ready to accept connections from ingress")
    _LOGGER.info("=" * 60)
    return runner


async def main():
    """Main function."""
    global manager

    _LOGGER.info("=" * 60)
    _LOGGER.info("Starting Squid Proxy Manager add-on v%s", APP_VERSION)
    _LOGGER.info("=" * 60)
    _LOGGER.info("Python version: %s", sys.version)
    _LOGGER.info("Log level: %s", LOG_LEVEL)
    _LOGGER.info("Config path: %s (exists: %s)", CONFIG_PATH, CONFIG_PATH.exists())
    _LOGGER.info("HA API URL: %s", HA_API_URL)

    runner = None
    try:
        # Start web API FIRST so ingress can connect even if manager init fails
        _LOGGER.info("Step 1/3: Starting web server...")
        runner = await start_app()
        _LOGGER.info("✓ Web server started successfully")
        _LOGGER.info("Server is now accessible via ingress")

        # Initialize manager with error handling
        _LOGGER.info("Step 2/3: Initializing ProxyInstanceManager...")
        try:
            manager = ProxyInstanceManager()
            _LOGGER.info("✓ Manager initialized successfully")
        except Exception as ex:
            _LOGGER.error("✗ Failed to initialize manager: %s", ex, exc_info=True)
            manager = None

        # Load configuration and create instances from config (only if manager is available)
        _LOGGER.info("Step 3/3: Loading configuration and creating instances...")
        if manager is not None:
            try:
                _LOGGER.info("Loading configuration from %s", CONFIG_PATH)
                config = await get_config()
                instances_config = config.get("instances", [])
                _LOGGER.info("Loaded configuration: %d instance(s) defined", len(instances_config))

                # Create instances from configuration
                for idx, instance_config in enumerate(instances_config, 1):
                    try:
                        name = instance_config.get("name")
                        port = instance_config.get("port", 3128)
                        https_enabled = instance_config.get("https_enabled", False)
                        users = instance_config.get("users", [])

                        _LOGGER.info(
                            "[%d/%d] Creating instance: name=%s, port=%d, https=%s, users=%d",
                            idx,
                            len(instances_config),
                            name,
                            port,
                            https_enabled,
                            len(users),
                        )
                        cert_params = instance_config.get("cert_params")
                        await manager.create_instance(
                            name=name,
                            port=port,
                            https_enabled=https_enabled,
                            users=users,
                            cert_params=cert_params,
                        )
                        _LOGGER.info("✓ Instance '%s' created successfully", name)
                    except Exception as ex:
                        _LOGGER.error(
                            "✗ Failed to create instance '%s': %s",
                            instance_config.get("name"),
                            ex,
                            exc_info=True,
                        )
                _LOGGER.info("Configuration processing complete")
            except Exception as ex:
                _LOGGER.error("✗ Failed to load configuration: %s", ex, exc_info=True)
        else:
            _LOGGER.warning("Skipping instance creation - manager not initialized")

        _LOGGER.info("=" * 60)
        _LOGGER.info("✓ Squid Proxy Manager add-on started successfully")
        _LOGGER.info("Server status: RUNNING")
        _LOGGER.info("Manager status: %s", "INITIALIZED" if manager else "NOT INITIALIZED")
        _LOGGER.info("Ready to accept requests")
        _LOGGER.info("=" * 60)

        # Keep running
        _LOGGER.info("Entering main event loop...")
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            _LOGGER.info("Received keyboard interrupt, shutting down...")
        except Exception as ex:
            _LOGGER.error("Unexpected error in main event loop: %s", ex, exc_info=True)
            raise
    except Exception as ex:
        _LOGGER.critical("Fatal error during startup: %s", ex, exc_info=True)
        _LOGGER.critical("Add-on failed to start properly")
        raise
    finally:
        _LOGGER.info("Cleaning up...")
        if runner:
            try:
                await runner.cleanup()
                _LOGGER.info("Server cleanup complete")
            except Exception as ex:
                _LOGGER.error("Error during cleanup: %s", ex, exc_info=True)
        _LOGGER.info("Shutdown complete")


if __name__ == "__main__":
    try:
        _LOGGER.info("Entering main execution block")
        _LOGGER.info("Starting asyncio event loop...")
        asyncio.run(main())
    except KeyboardInterrupt:
        if "_LOGGER" in globals():
            _LOGGER.info("Interrupted by user")
        else:
            print("Interrupted by user", file=sys.stderr)
        sys.exit(0)
    except Exception as ex:
        if "_LOGGER" in globals():
            _LOGGER.critical("Fatal error in main execution: %s", ex, exc_info=True)
        else:
            print(f"CRITICAL: Fatal error in main execution: {ex}", file=sys.stderr)
            import traceback

            traceback.print_exc()
        sys.exit(1)
