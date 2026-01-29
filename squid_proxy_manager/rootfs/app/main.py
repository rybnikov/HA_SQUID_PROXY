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
CONFIG_PATH = Path("/data/options.json")
HA_API_URL = os.getenv("SUPERVISOR", "http://supervisor")
HA_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")

# Manager will be initialized in main()
manager = None


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
        "version": "1.0.21",
        "api": "/api",
        "manager_initialized": manager is not None,
    }
    _LOGGER.info("Root endpoint accessed - manager initialized: %s", manager is not None)
    return web.json_response(response_data)


async def web_ui_handler(request):
    """Serve web UI HTML page."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Squid Proxy Manager</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #4a9eff;
            margin-bottom: 10px;
        }
        .status {
            padding: 10px;
            border-radius: 5px;
            margin: 20px 0;
            background: #2a2a2a;
        }
        .status.ok { border-left: 4px solid #4caf50; }
        .status.error { border-left: 4px solid #f44336; }
        .instances {
            margin-top: 30px;
        }
        .instance-card {
            background: #2a2a2a;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #4a9eff;
        }
        .instance-name {
            font-size: 1.2em;
            font-weight: bold;
            color: #4a9eff;
            margin-bottom: 10px;
        }
        .btn {
            background: #4a9eff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px 5px 5px 0;
        }
        .btn:hover { background: #357abd; }
        .btn.danger { background: #f44336; }
        .btn.danger:hover { background: #d32f2f; }
        .loading { text-align: center; padding: 20px; }
        .error { color: #f44336; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐙 Squid Proxy Manager</h1>
        <div id="status" class="status loading">Loading...</div>
        <div id="instances" class="instances"></div>
    </div>
    <script>
        async function loadInstances() {
            try {
                const response = await fetch('/api/instances');
                if (!response.ok) {
                    throw new Error('Failed to load instances');
                }
                const data = await response.json();
                updateUI(data);
            } catch (error) {
                document.getElementById('status').innerHTML =
                    '<div class="error">Error: ' + error.message + '</div>';
            }
        }

        function updateUI(data) {
            const statusEl = document.getElementById('status');
            const instancesEl = document.getElementById('instances');

            if (data.error) {
                statusEl.className = 'status error';
                statusEl.innerHTML = '<div class="error">' + data.error + '</div>';
                return;
            }

            statusEl.className = 'status ok';
            statusEl.innerHTML = 'Service Status: <strong>Running</strong> | Instances: ' + data.count;

            if (data.instances && data.instances.length > 0) {
                instancesEl.innerHTML = '<h2>Proxy Instances</h2>' +
                    data.instances.map(instance => `
                        <div class="instance-card">
                            <div class="instance-name">${instance.name}</div>
                            <div>Port: ${instance.port} | HTTPS: ${instance.https_enabled ? 'Yes' : 'No'}</div>
                            <div>Status: ${instance.status || 'unknown'}</div>
                            <button class="btn" onclick="startInstance('${instance.name}')">Start</button>
                            <button class="btn" onclick="stopInstance('${instance.name}')">Stop</button>
                        </div>
                    `).join('');
            } else {
                instancesEl.innerHTML = '<p>No instances configured. Use the API to create instances.</p>';
            }
        }

        async function startInstance(name) {
            try {
                const response = await fetch(`/api/instances/${name}/start`, { method: 'POST' });
                const data = await response.json();
                if (data.status === 'started') {
                    loadInstances();
                } else {
                    alert('Error: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        async function stopInstance(name) {
            try {
                const response = await fetch(`/api/instances/${name}/stop`, { method: 'POST' });
                const data = await response.json();
                if (data.status === 'stopped') {
                    loadInstances();
                } else {
                    alert('Error: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        // Load instances on page load and refresh every 5 seconds
        loadInstances();
        setInterval(loadInstances, 5000);
    </script>
</body>
</html>"""
    return web.Response(text=html_content, content_type="text/html")


async def health_check(request):
    """Health check endpoint."""
    _LOGGER.debug("Health check called from %s", request.remote)
    health_status = {
        "status": "ok",
        "service": "squid_proxy_manager",
        "manager_initialized": manager is not None,
        "version": "1.0.21",
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

        if not name:
            return web.json_response({"error": "Instance name is required"}, status=400)

        instance = await manager.create_instance(
            name=name,
            port=port,
            https_enabled=https_enabled,
            users=users,
        )

        return web.json_response({"status": "created", "instance": instance}, status=201)
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

        success = await manager.stop_instance(name)
        if success:
            return web.json_response({"status": "stopped", "instance": name})
        else:
            return web.json_response({"error": "Failed to stop instance"}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to stop instance: %s", ex)
        return web.json_response({"error": str(ex)}, status=500)


async def remove_instance(request):
    """Remove a proxy instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        if not name:
            return web.json_response({"error": "Instance name is required"}, status=400)

        success = await manager.remove_instance(name)
        if success:
            return web.json_response({"status": "removed", "instance": name})
        else:
            return web.json_response({"error": "Failed to remove instance"}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to remove instance: %s", ex)
        return web.json_response({"error": str(ex)}, status=500)


async def start_app():
    """Start the web application."""
    _LOGGER.info("Initializing web application...")
    app = web.Application()

    # Add middleware for path normalization (handle multiple slashes from ingress)
    @web.middleware
    async def normalize_path_middleware(request, handler):
        # Normalize multiple slashes to single slash
        import re

        original_path = request.path
        normalized_path = re.sub(r"/+", "/", original_path)

        # If path was normalized, redirect to normalized path
        if normalized_path != original_path:
            _LOGGER.debug("Normalizing path: %s -> %s", original_path, normalized_path)
            # For paths like //// -> /, serve the root handler directly
            if normalized_path == "/":
                return await root_handler(request)
            # Otherwise, let aiohttp handle the normalized path
            # We'll just log it and continue - aiohttp will match the route

        return await handler(request)

    # Add middleware for request logging
    @web.middleware
    async def logging_middleware(request, handler):
        _LOGGER.debug("Request: %s %s from %s", request.method, request.path_qs, request.remote)
        try:
            response = await handler(request)
            _LOGGER.debug("Response: %s %s -> %d", request.method, request.path_qs, response.status)
            return response
        except Exception as ex:
            _LOGGER.error(
                "Unhandled exception in handler for %s %s: %s",
                request.method,
                request.path_qs,
                ex,
                exc_info=True,
            )
            raise

    app.middlewares.append(normalize_path_middleware)
    app.middlewares.append(logging_middleware)

    # Root and health routes (for ingress health checks)
    # With ingress_entry: /, all routes are accessible directly
    _LOGGER.info("Registering routes...")
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_check)

    # API routes
    app.router.add_get("/api/instances", get_instances)
    app.router.add_post("/api/instances", create_instance)
    app.router.add_post("/api/instances/{name}/start", start_instance)
    app.router.add_post("/api/instances/{name}/stop", stop_instance)
    app.router.add_delete("/api/instances/{name}", remove_instance)

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
        site = web.TCPSite(runner, "0.0.0.0", port)
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
        os.getenv("SUPERVISOR_TOKEN", "unknown")[:8]
        if os.getenv("SUPERVISOR_TOKEN")
        else "unknown",
    )
    _LOGGER.info("  Server is ready to accept connections from ingress")
    _LOGGER.info("=" * 60)
    return runner


async def main():
    """Main function."""
    global manager

    _LOGGER.info("=" * 60)
    _LOGGER.info("Starting Squid Proxy Manager add-on v1.0.21")
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
            _LOGGER.error("API will run in degraded mode (503 responses for instance operations)")
            _LOGGER.error("Docker connection may be unavailable. Check Docker socket permissions.")
            _LOGGER.error("Docker socket path: /var/run/docker.sock")
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
                        await manager.create_instance(
                            name=name,
                            port=port,
                            https_enabled=https_enabled,
                            users=users,
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
