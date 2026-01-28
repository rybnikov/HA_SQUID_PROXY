#!/usr/bin/env python3
"""Main entry point for Squid Proxy Manager add-on."""
import asyncio
import json
import logging
import os
from pathlib import Path

import aiohttp
from aiohttp import web
import sys

# Add app directory to path
sys.path.insert(0, '/app')

from proxy_manager import ProxyInstanceManager

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
_LOGGER = logging.getLogger(__name__)

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


async def root_handler(request):
    """Root endpoint for ingress."""
    _LOGGER.debug("Root handler called from %s", request.remote)
    response_data = {
        "status": "ok",
        "service": "squid_proxy_manager",
        "version": "1.0.3",
        "api": "/api",
        "manager_initialized": manager is not None
    }
    _LOGGER.info("Root endpoint accessed - manager initialized: %s", manager is not None)
    return web.json_response(response_data)


async def health_check(request):
    """Health check endpoint."""
    _LOGGER.debug("Health check called from %s", request.remote)
    health_status = {
        "status": "ok",
        "service": "squid_proxy_manager",
        "manager_initialized": manager is not None,
        "version": "1.0.2"
    }
    _LOGGER.info("Health check - status: ok, manager: %s", "initialized" if manager else "not initialized")
    return web.json_response(health_status)


async def get_instances(request):
    """Get list of proxy instances."""
    _LOGGER.debug("GET /api/instances called from %s", request.remote)
    if manager is None:
        _LOGGER.warning("GET /api/instances called but manager is not initialized")
        return web.json_response(
            {"error": "Manager not initialized"}, status=503
        )
    try:
        _LOGGER.info("Retrieving list of proxy instances")
        instances = await manager.get_instances()
        _LOGGER.info("Retrieved %d proxy instances", len(instances))
        return web.json_response({"instances": instances, "count": len(instances)})
    except Exception as ex:
        _LOGGER.error("Failed to get instances: %s", ex, exc_info=True)
        return web.json_response(
            {"error": str(ex)}, status=500
        )


async def create_instance(request):
    """Create a new proxy instance."""
    if manager is None:
        return web.json_response(
            {"error": "Manager not initialized"}, status=503
        )
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
        return web.json_response(
            {"error": "Manager not initialized"}, status=503
        )
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
        return web.json_response(
            {"error": "Manager not initialized"}, status=503
        )
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
        return web.json_response(
            {"error": "Manager not initialized"}, status=503
        )
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
    
    # Add middleware for request logging
    @web.middleware
    async def logging_middleware(request, handler):
        _LOGGER.debug("Request: %s %s from %s", request.method, request.path_qs, request.remote)
        try:
            response = await handler(request)
            _LOGGER.debug("Response: %s %s -> %d", request.method, request.path_qs, response.status)
            return response
        except Exception as ex:
            _LOGGER.error("Unhandled exception in handler for %s %s: %s", 
                         request.method, request.path_qs, ex, exc_info=True)
            raise
    
    app.middlewares.append(logging_middleware)
    
    # Root and health routes (for ingress health checks)
    _LOGGER.info("Registering routes...")
    app.router.add_get("/", root_handler)
    app.router.add_get("/api", root_handler)
    app.router.add_get("/health", health_check)
    
    # API routes (with /api prefix for ingress_entry)
    app.router.add_get("/api/instances", get_instances)
    app.router.add_post("/api/instances", create_instance)
    app.router.add_post("/api/instances/{name}/start", start_instance)
    app.router.add_post("/api/instances/{name}/stop", stop_instance)
    app.router.add_delete("/api/instances/{name}", remove_instance)
    
    # Also add routes without /api prefix (in case ingress strips it)
    app.router.add_get("/instances", get_instances)
    app.router.add_post("/instances", create_instance)
    app.router.add_post("/instances/{name}/start", start_instance)
    app.router.add_post("/instances/{name}/stop", stop_instance)
    app.router.add_delete("/instances/{name}", remove_instance)
    
    _LOGGER.info("Routes registered: /, /api, /health, /api/instances, /instances")

    _LOGGER.info("Setting up AppRunner...")
    runner = web.AppRunner(app)
    await runner.setup()
    _LOGGER.info("AppRunner setup complete")
    
    _LOGGER.info("Starting TCP site on 0.0.0.0:8099...")
    site = web.TCPSite(runner, "0.0.0.0", 8099)
    await site.start()
    _LOGGER.info("TCP site started successfully")

    _LOGGER.info("✓ Squid Proxy Manager API started on port 8099")
    _LOGGER.info("Server is ready to accept connections")
    return runner


async def main():
    """Main function."""
    global manager
    
    _LOGGER.info("=" * 60)
    _LOGGER.info("Starting Squid Proxy Manager add-on v1.0.2")
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
        _LOGGER.info("✓ Web server started successfully on port 8099")
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

                        _LOGGER.info("[%d/%d] Creating instance: name=%s, port=%d, https=%s, users=%d",
                                   idx, len(instances_config), name, port, https_enabled, len(users))
                        await manager.create_instance(
                            name=name,
                            port=port,
                            https_enabled=https_enabled,
                            users=users,
                        )
                        _LOGGER.info("✓ Instance '%s' created successfully", name)
                    except Exception as ex:
                        _LOGGER.error("✗ Failed to create instance '%s': %s", 
                                    instance_config.get('name'), ex, exc_info=True)
                _LOGGER.info("Configuration processing complete")
            except Exception as ex:
                _LOGGER.error("✗ Failed to load configuration: %s", ex, exc_info=True)
        else:
            _LOGGER.warning("Skipping instance creation - manager not initialized")

        _LOGGER.info("=" * 60)
        _LOGGER.info("✓ Squid Proxy Manager add-on started successfully")
        _LOGGER.info("Server status: RUNNING")
        _LOGGER.info("Manager status: %s", "INITIALIZED" if manager else "NOT INITIALIZED")
        _LOGGER.info("Ready to accept requests on port 8099")
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
        _LOGGER.info("Python script started")
        asyncio.run(main())
    except KeyboardInterrupt:
        _LOGGER.info("Interrupted by user")
        sys.exit(0)
    except Exception as ex:
        _LOGGER.critical("Fatal error: %s", ex, exc_info=True)
        sys.exit(1)
