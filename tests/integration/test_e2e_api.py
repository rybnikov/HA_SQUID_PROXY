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
        assert any(i["name"] == test_instance_name for i in data["instances"])

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
