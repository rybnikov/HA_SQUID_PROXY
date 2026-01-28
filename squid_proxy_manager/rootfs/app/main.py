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
    return web.json_response({
        "status": "ok",
        "service": "squid_proxy_manager",
        "version": "1.0.1",
        "api": "/api"
    })


async def health_check(request):
    """Health check endpoint."""
    return web.json_response({"status": "ok", "service": "squid_proxy_manager"})


async def get_instances(request):
    """Get list of proxy instances."""
    if manager is None:
        return web.json_response(
            {"error": "Manager not initialized"}, status=503
        )
    try:
        instances = await manager.get_instances()
        return web.json_response({"instances": instances, "count": len(instances)})
    except Exception as ex:
        _LOGGER.error("Failed to get instances: %s", ex)
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
    app = web.Application()
    
    # Root and health routes (for ingress health checks)
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

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8099)
    await site.start()

    _LOGGER.info("Squid Proxy Manager API started on port 8099")
    return runner


async def main():
    """Main function."""
    global manager
    
    _LOGGER.info("Starting Squid Proxy Manager add-on...")

    # Start web API FIRST so ingress can connect even if manager init fails
    runner = await start_app()
    _LOGGER.info("Web server started, initializing manager...")

    # Initialize manager with error handling
    try:
        manager = ProxyInstanceManager()
        _LOGGER.info("Manager initialized successfully")
    except Exception as ex:
        _LOGGER.error("Failed to initialize manager: %s. API will run in degraded mode.", ex)
        _LOGGER.error("Docker connection may be unavailable. Check Docker socket permissions.")
        manager = None

    # Load configuration and create instances from config (only if manager is available)
    if manager is not None:
        try:
            config = await get_config()
            instances_config = config.get("instances", [])
            _LOGGER.info(f"Loaded configuration: {len(instances_config)} instances defined")

            # Create instances from configuration
            for instance_config in instances_config:
                try:
                    name = instance_config.get("name")
                    port = instance_config.get("port", 3128)
                    https_enabled = instance_config.get("https_enabled", False)
                    users = instance_config.get("users", [])

                    _LOGGER.info(f"Creating instance from config: {name} on port {port}")
                    await manager.create_instance(
                        name=name,
                        port=port,
                        https_enabled=https_enabled,
                        users=users,
                    )
                except Exception as ex:
                    _LOGGER.error(f"Failed to create instance {instance_config.get('name')}: {ex}")
        except Exception as ex:
            _LOGGER.error(f"Failed to load configuration: {ex}")
    else:
        _LOGGER.warning("Skipping instance creation - manager not initialized")

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        _LOGGER.info("Shutting down...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
