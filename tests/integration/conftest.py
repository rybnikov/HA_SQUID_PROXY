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

if "-z" in sys.argv:
    # Just exit success for cache initialization
    sys.exit(0)

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
log_dir = os.path.join(os.path.dirname(os.path.dirname(config_file)), "logs", os.path.basename(os.path.dirname(config_file)))
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "cache.log")

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
async def app_with_manager(temp_data_dir, squid_installed):
    """Provide an aiohttp app with ProxyInstanceManager using real main.py handlers."""
    import main
    from aiohttp.web import AppKey
    from proxy_manager import ProxyInstanceManager

    # Use temporary directory for /data
    config_dir = temp_data_dir / "squid_proxy_manager"
    certs_dir = config_dir / "certs"
    logs_dir = config_dir / "logs"

    # Create directories
    certs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Start patches (they'll stay active for the fixture lifetime)
    patches = [
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", config_dir),
        patch("proxy_manager.CERTS_DIR", certs_dir),
        patch("proxy_manager.LOGS_DIR", logs_dir),
        patch("proxy_manager.SQUID_BINARY", squid_installed),
        patch("main.CONFIG_PATH", temp_data_dir / "options.json"),
    ]
    for p in patches:
        p.start()

    try:
        manager = ProxyInstanceManager()
        # Set the global manager in main module
        main.manager = manager

        MANAGER_KEY = AppKey("manager", t=ProxyInstanceManager)

        app = web.Application()
        app.middlewares.append(main.normalize_path_middleware)
        app.middlewares.append(main.logging_middleware)

        app.router.add_get("/", main.root_handler)
        app.router.add_get("/health", main.health_check)
        app.router.add_get("/api/instances", main.get_instances)
        app.router.add_post("/api/instances", main.create_instance)
        app.router.add_patch("/api/instances/{name}", main.update_instance_settings)
        app.router.add_post("/api/instances/{name}/start", main.start_instance)
        app.router.add_post("/api/instances/{name}/stop", main.stop_instance)
        app.router.add_delete("/api/instances/{name}", main.remove_instance)
        app.router.add_post("/api/instances/{name}/certs", main.regenerate_instance_certs)
        app.router.add_get("/api/instances/{name}/logs", main.get_instance_logs)

        # User management API
        app.router.add_get("/api/instances/{name}/users", main.get_instance_users)
        app.router.add_post("/api/instances/{name}/users", main.add_instance_user)
        app.router.add_delete("/api/instances/{name}/users/{username}", main.remove_instance_user)

        app[MANAGER_KEY] = manager

        yield app
    finally:
        # Cleanup: stop all processes
        if manager:
            for name in list(manager.processes.keys()):
                # Use a small timeout for stopping
                try:
                    # We can't easily use await here if the loop is closing,
                    # but app_with_manager is an async fixture so it's fine.
                    await manager.stop_instance(name)
                except Exception:
                    pass

        # Reset main.manager
        main.manager = None
        # Stop patches
        for p in patches:
            p.stop()
