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
