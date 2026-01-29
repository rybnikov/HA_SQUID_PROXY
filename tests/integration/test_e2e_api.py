"""E2E tests for the web interface and API endpoints (Process-based)."""
import pytest
from aiohttp.test_utils import TestClient, TestServer


@pytest.mark.asyncio
async def test_web_ui_loading(app_with_manager):
    """Test that the web UI HTML is served correctly."""
    async with TestClient(TestServer(app_with_manager)) as client:
        # Request with Accept: text/html
        headers = {"Accept": "text/html"}
        resp = await client.get("/", headers=headers)
        assert resp.status == 200
        assert resp.content_type == "text/html"
        text = await resp.text()
        assert "Squid Proxy Manager" in text
        assert "🐙" in text
        # Verify relative paths are used in JavaScript
        assert "fetch('api/instances')" in text
        assert "fetch(`api/instances/${name}/start`" in text
        assert "fetch(`api/instances/${name}/stop`" in text


@pytest.mark.asyncio
async def test_path_normalization_e2e(app_with_manager):
    """Test that multiple slashes in path are normalized correctly."""
    async with TestClient(TestServer(app_with_manager)) as client:
        # Test root with multiple slashes
        # Using URL object to avoid TestClient's absolute URL check for "//"
        from yarl import URL

        resp = await client.get(URL("/").with_path("///"))
        assert resp.status == 200

        # Test API with multiple slashes
        resp = await client.get(URL("/").with_path("//api//instances"))
        assert resp.status == 200
        data = await resp.json()
        assert "instances" in data


@pytest.mark.asyncio
async def test_path_normalization_with_match_info_e2e(
    app_with_manager, test_instance_name, test_port
):
    """Test that path normalization works for routes with match_info (e.g. /api/instances/{name})."""
    async with TestClient(TestServer(app_with_manager)) as client:
        # 1. Create instance normally
        await client.post("/api/instances", json={"name": test_instance_name, "port": test_port})

        # 2. Try to stop it using a path with double slashes
        from yarl import URL

        path = f"//api//instances//{test_instance_name}//stop"
        resp = await client.post(URL("/").with_path(path))

        # This will fail if match_info is not correctly passed to the handler
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "stopped"


@pytest.mark.asyncio
async def test_error_logging_visibility(app_with_manager, caplog):
    """Test that errors (4xx/5xx) are logged at INFO level for visibility."""
    import logging

    # Set caplog to INFO to capture INFO level logs
    caplog.set_level(logging.INFO)

    async with TestClient(TestServer(app_with_manager)) as client:
        # Trigger a 404
        resp = await client.get("/nonexistent-path")
        assert resp.status == 404

        # Check logs - our middleware should log this at INFO level
        assert any(
            "Response: GET /nonexistent-path -> 404" in record.message for record in caplog.records
        )
        # Verify it was logged at INFO level (not just captured because we set caplog to INFO)
        info_records = [
            record
            for record in caplog.records
            if "404" in record.message and record.levelno == logging.INFO
        ]
        assert len(info_records) > 0


@pytest.mark.asyncio
async def test_api_instance_operations_e2e(app_with_manager, test_instance_name, test_port):
    """Test full API flow for instance management via HTTP."""
    async with TestClient(TestServer(app_with_manager)) as client:
        # 1. Create instance
        resp = await client.post(
            "/api/instances",
            json={
                "name": test_instance_name,
                "port": test_port,
                "https_enabled": False,
                "users": [{"username": "user1", "password": "password123"}],
            },
        )
        assert resp.status == 201
        data = await resp.json()
        assert data["status"] == "created"

        # 2. List instances
        resp = await client.get("/api/instances")
        assert resp.status == 200
        data = await resp.json()
        assert any(
            i["name"] == test_instance_name
            and i["port"] == test_port
            and i["https_enabled"] is False
            for i in data["instances"]
        )

        # 3. Stop instance
        resp = await client.post(f"/api/instances/{test_instance_name}/stop")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "stopped"

        # 4. Start instance
        resp = await client.post(f"/api/instances/{test_instance_name}/start")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "started"

        # 5. Delete instance
        resp = await client.delete(f"/api/instances/{test_instance_name}")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "removed"


@pytest.mark.asyncio
async def test_user_management_e2e(app_with_manager, test_instance_name, test_port):
    """Test user management via API."""
    async with TestClient(TestServer(app_with_manager)) as client:
        # 1. Create instance
        await client.post("/api/instances", json={"name": test_instance_name, "port": test_port})

        # 2. Add user
        resp = await client.post(
            f"/api/instances/{test_instance_name}/users",
            json={"username": "newuser", "password": "password123"},
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "user_added"

        # 3. List users
        resp = await client.get(f"/api/instances/{test_instance_name}/users")
        assert resp.status == 200
        data = await resp.json()
        assert "newuser" in data["users"]

        # 4. Remove user
        resp = await client.delete(f"/api/instances/{test_instance_name}/users/newuser")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "user_removed"

        # 5. Verify user is gone
        resp = await client.get(f"/api/instances/{test_instance_name}/users")
        data = await resp.json()
        assert "newuser" not in data["users"]


@pytest.mark.asyncio
async def test_instance_settings_e2e(app_with_manager, test_instance_name, test_port):
    """Test instance settings updates via API."""
    async with TestClient(TestServer(app_with_manager)) as client:
        # 1. Create instance
        await client.post("/api/instances", json={"name": test_instance_name, "port": test_port})

        # 2. Update port and enable HTTPS
        new_port = test_port + 1
        resp = await client.patch(
            f"/api/instances/{test_instance_name}",
            json={"port": new_port, "https_enabled": True},
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "updated"

        # 3. Verify settings were applied
        resp = await client.get("/api/instances")
        data = await resp.json()
        instance = next(i for i in data["instances"] if i["name"] == test_instance_name)
        assert instance["port"] == new_port
        assert instance["https_enabled"] is True

        # 4. Regenerate certificates
        resp = await client.post(f"/api/instances/{test_instance_name}/certs")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "certs_regenerated"

        # 5. Get logs
        resp = await client.get(f"/api/instances/{test_instance_name}/logs?type=cache")
        assert resp.status == 200
        text = await resp.text()
        assert len(text) > 0


@pytest.mark.asyncio
async def test_instance_with_spaces_e2e(app_with_manager, test_port):
    """Verify that instances with spaces in their name work correctly."""
    instance_name = "test 1"
    async with TestClient(TestServer(app_with_manager)) as client:
        # 1. Create instance with spaces
        resp = await client.post(
            "/api/instances",
            json={"name": instance_name, "port": test_port},
        )
        assert resp.status == 201

        # 2. Start it
        resp = await client.post(f"/api/instances/{instance_name}/start")
        assert resp.status == 200

        # 3. Verify it is running
        resp = await client.get("/api/instances")
        data = await resp.json()
        instance = next(i for i in data["instances"] if i["name"] == instance_name)
        assert instance["running"] is True

        # 4. Check that logs are accessible
        # Wait a bit for Squid to write something
        import asyncio

        await asyncio.sleep(1)
        resp = await client.get(f"/api/instances/{instance_name}/logs?type=cache")
        assert resp.status == 200
        text = await resp.text()
        assert "Log file cache.log not found" not in text
        assert len(text) > 0
