"""Shared fixtures and configuration for integration tests.

Integration tests for process-based architecture.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from aiohttp import web

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../squid_proxy_manager/rootfs/app"))


@pytest.fixture(scope="session")
def session_temp_dir():
    """Provide a session-scoped temporary directory."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope="session")
def squid_installed(session_temp_dir):
    """Check if Squid binary is installed or provide a fake one for testing.

    This ensures tests can run even if Squid isn't installed locally,
    while still verifying the process management logic.
    """
    squid_path = shutil.which("squid")
    if not squid_path:
        # Try common paths
        for path in ["/usr/sbin/squid", "/usr/local/sbin/squid"]:
            if os.path.exists(path):
                squid_path = path
                break

    if not squid_path:
        # Create a fake squid script for testing process management
        fake_squid = session_temp_dir / "fake_squid"
        fake_squid.write_text(
            r"""#!/usr/bin/env python3
import time
import sys
import socket
import re
import os

# Simple fake squid that listens on the configured port
config_file = None
for i, arg in enumerate(sys.argv):
    if arg == "-f" and i + 1 < len(sys.argv):
        config_file = sys.argv[i+1]
        break

port = 3128
if config_file:
    try:
        with open(config_file, 'r') as f:
            content = f.read()
            match = re.search(r'http_port (\d+)', content)
            if match:
                port = int(match.group(1))
    except Exception:
        pass

# Log startup
log_file = os.path.join(os.path.dirname(config_file), "fake_squid.log") if config_file else "fake_squid.log"
with open(log_file, "a") as f:
    f.write(f"Fake Squid starting on port {port}\n")

# Listen on the port
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('127.0.0.1', port))
    s.listen(1)
    with open(log_file, "a") as f:
        f.write(f"Fake Squid listening on {port}\n")
    while True:
        time.sleep(1)
except Exception as e:
    with open(log_file, "a") as f:
        f.write(f"Error: {e}\n")
    sys.exit(1)
"""
        )
        fake_squid.chmod(0o755)
        return str(fake_squid)

    return squid_path


@pytest.fixture
def temp_data_dir():
    """Provide a temporary directory for /data."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
async def proxy_manager(temp_data_dir, squid_installed):
    """Provide a ProxyInstanceManager instance using processes.

    Patches DATA_DIR and SQUID_BINARY to use test-safe values.
    """
    from proxy_manager import ProxyInstanceManager

    config_dir = temp_data_dir / "squid_proxy_manager"
    certs_dir = config_dir / "certs"
    logs_dir = config_dir / "logs"

    # Create directories
    certs_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)

    with patch("proxy_manager.DATA_DIR", temp_data_dir), patch(
        "proxy_manager.CONFIG_DIR", config_dir
    ), patch("proxy_manager.CERTS_DIR", certs_dir), patch(
        "proxy_manager.LOGS_DIR", logs_dir
    ), patch(
        "proxy_manager.SQUID_BINARY", squid_installed
    ):
        manager = ProxyInstanceManager()
        yield manager

        # Cleanup: stop all processes
        for name in list(manager.processes.keys()):
            await manager.stop_instance(name)


@pytest.fixture
def test_instance_name():
    """Provide a unique test instance name."""
    import uuid

    return f"test_proxy_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_port():
    """Provide a test port that's unlikely to conflict."""
    import random

    return random.randint(20000, 30000)


@pytest.fixture
async def app_with_manager(proxy_manager, temp_data_dir):
    """Provide an aiohttp app with ProxyInstanceManager."""
    from aiohttp.web import AppKey
    from proxy_manager import ProxyInstanceManager

    manager = proxy_manager

    async def root_handler(request):
        accept_header = request.headers.get("Accept", "")
        if "text/html" in accept_header:
            return web.Response(
                text="<html><body>🐙 Squid Proxy Manager</body></html>", content_type="text/html"
            )
        return await health_check(request)

    async def health_check(request):
        return web.json_response(
            {
                "status": "ok",
                "manager_initialized": manager is not None,
                "processes_count": len(manager.processes) if manager else 0,
            }
        )

    async def get_instances(request):
        if manager is None:
            return web.json_response({"error": "Manager not initialized"}, status=503)
        instances = await manager.get_instances()
        return web.json_response({"instances": instances, "count": len(instances)})

    async def create_instance(request):
        if manager is None:
            return web.json_response({"error": "Manager not initialized"}, status=503)
        try:
            data = await request.json()
            instance = await manager.create_instance(
                name=data.get("name"),
                port=data.get("port", 3128),
                https_enabled=data.get("https_enabled", False),
                users=data.get("users", []),
            )
            return web.json_response({"status": "created", "instance": instance}, status=201)
        except Exception as ex:
            return web.json_response({"error": str(ex)}, status=500)

    async def start_instance(request):
        if manager is None:
            return web.json_response({"error": "Manager not initialized"}, status=503)
        name = request.match_info.get("name")
        success = await manager.start_instance(name)
        if success:
            return web.json_response({"status": "started"})
        return web.json_response({"error": "Failed to start"}, status=500)

    async def stop_instance(request):
        if manager is None:
            return web.json_response({"error": "Manager not initialized"}, status=503)
        name = request.match_info.get("name")
        success = await manager.stop_instance(name)
        if success:
            return web.json_response({"status": "stopped"})
        return web.json_response({"error": "Failed to stop"}, status=500)

    async def delete_instance(request):
        if manager is None:
            return web.json_response({"error": "Manager not initialized"}, status=503)
        name = request.match_info.get("name")
        success = await manager.remove_instance(name)
        if success:
            return web.json_response({"status": "removed"})
        return web.json_response({"error": "Failed to remove"}, status=500)

    MANAGER_KEY = AppKey("manager", t=ProxyInstanceManager)

    app = web.Application()
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_check)
    app.router.add_get("/api/instances", get_instances)
    app.router.add_post("/api/instances", create_instance)
    app.router.add_post("/api/instances/{name}/start", start_instance)
    app.router.add_post("/api/instances/{name}/stop", stop_instance)
    app.router.add_delete("/api/instances/{name}", delete_instance)

    app[MANAGER_KEY] = manager

    return app
