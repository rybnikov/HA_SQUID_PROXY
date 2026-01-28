#!/usr/bin/env python3
"""Main entry point for Squid Proxy Manager add-on."""
import asyncio
import json
import logging
import os
from pathlib import Path

import aiohttp
from aiohttp import web

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


async def get_config():
    """Load add-on configuration."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


async def health_check(request):
    """Health check endpoint."""
    return web.json_response({"status": "ok"})


async def get_instances(request):
    """Get list of proxy instances."""
    config = await get_config()
    instances = config.get("instances", [])
    return web.json_response({"instances": instances})


async def create_instance(request):
    """Create a new proxy instance."""
    data = await request.json()
    # Implementation here
    return web.json_response({"status": "created", "instance": data})


async def start_app():
    """Start the web application."""
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_get("/api/instances", get_instances)
    app.router.add_post("/api/instances", create_instance)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8099)
    await site.start()

    _LOGGER.info("Squid Proxy Manager API started on port 8099")
    return runner


async def main():
    """Main function."""
    _LOGGER.info("Starting Squid Proxy Manager add-on...")

    # Load configuration
    config = await get_config()
    _LOGGER.info(f"Loaded configuration: {len(config.get('instances', []))} instances")

    # Start web API
    runner = await start_app()

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        _LOGGER.info("Shutting down...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
