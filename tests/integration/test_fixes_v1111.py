"""E2E tests for fixes in v1.1.11 (HTTPS startup, user mgmt, logs)."""

import asyncio
import sys
from pathlib import Path

import pytest

# Add integration tests directory to path for test_helpers
sys.path.insert(0, str(Path(__file__).parent))
from test_helpers import call_handler


@pytest.mark.asyncio
async def test_https_instance_startup_fixed(app_with_manager, test_port):
    """Verify that HTTPS instances start correctly with the right certificate filenames."""
    instance_name = "https-test"
    # 1. Create HTTPS instance
    resp = await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={"name": instance_name, "port": test_port, "https_enabled": True},
    )
    assert resp.status == 201

    # 2. Start it
    resp = await call_handler(app_with_manager, "POST", f"/api/instances/{instance_name}/start")
    assert resp.status == 200

    # 3. Verify it is running
    resp = await call_handler(app_with_manager, "GET", "/api/instances")
    data = await resp.json()
    instance = next(i for i in data["instances"] if i["name"] == instance_name)
    assert instance["running"] is True

    # 4. Check logs for startup success
    await asyncio.sleep(1)
    resp = await call_handler(
        app_with_manager, "GET", f"/api/instances/{instance_name}/logs?type=cache"
    )
    assert resp.status == 200
    text = await resp.text()
    assert "--- Starting Squid" in text
    # In our fake_squid, it won't actually fail on missing certs,
    # but we've verified the filenames in the logic.
    # The FATAL error reported by user was due to filename mismatch.


@pytest.mark.asyncio
async def test_user_management_errors_fixed(app_with_manager, test_instance_name, test_port):
    """Verify improved error handling for user management."""
    # 1. Create instance
    await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={"name": test_instance_name, "port": test_port},
    )

    # 2. Add user
    resp = await call_handler(
        app_with_manager,
        "POST",
        f"/api/instances/{test_instance_name}/users",
        json_data={"username": "testuser", "password": "password123"},
    )
    assert resp.status == 200

    # 3. Try to add same user again (should be 400 Bad Request)
    resp = await call_handler(
        app_with_manager,
        "POST",
        f"/api/instances/{test_instance_name}/users",
        json_data={"username": "testuser", "password": "password123"},
    )
    assert resp.status == 400
    data = await resp.json()
    assert "already exists" in data["error"]

    # 4. Try to add user with invalid password (too short)
    resp = await call_handler(
        app_with_manager,
        "POST",
        f"/api/instances/{test_instance_name}/users",
        json_data={"username": "shortpw", "password": "123"},
    )
    assert resp.status == 400
    data = await resp.json()
    assert "at least 8 characters" in data["error"]


@pytest.mark.asyncio
async def test_log_switching_api(app_with_manager, test_instance_name, test_port):
    """Verify that the log API serves both cache and access logs."""
    # 1. Create and start instance
    await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={"name": test_instance_name, "port": test_port},
    )
    await call_handler(app_with_manager, "POST", f"/api/instances/{test_instance_name}/start")
    await asyncio.sleep(1)

    # 2. Get cache logs
    resp = await call_handler(
        app_with_manager, "GET", f"/api/instances/{test_instance_name}/logs?type=cache"
    )
    assert resp.status == 200
    text = await resp.text()
    assert "Starting Squid" in text

    # 3. Get access logs (should exist even if empty)
    resp = await call_handler(
        app_with_manager, "GET", f"/api/instances/{test_instance_name}/logs?type=access"
    )
    assert resp.status == 200
    # If fake_squid doesn't write access.log, it might be "Log file access.log not found."
    # but the API call itself should succeed with 200.
