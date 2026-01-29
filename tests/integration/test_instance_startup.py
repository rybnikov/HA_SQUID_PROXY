"""Tests to ensure that default and new instances are correctly started and running."""
import asyncio
import json

import pytest
from aiohttp.test_utils import TestClient, TestServer


@pytest.mark.asyncio
async def test_default_instance_lifecycle(app_with_manager):
    """Test that a 'default' instance can be created, started, and verified as running."""
    async with TestClient(TestServer(app_with_manager)) as client:
        # 1. Create 'default' instance
        resp = await client.post(
            "/api/instances",
            json={"name": "default", "port": 3128, "https_enabled": False},
        )
        assert resp.status == 201

        # 2. Start it
        resp = await client.post("/api/instances/default/start")
        assert resp.status == 200

        # 3. Verify it's running via API
        resp = await client.get("/api/instances")
        data = await resp.json()
        instance = next((i for i in data["instances"] if i["name"] == "default"), None)
        assert instance is not None
        assert instance.get("running") is True
        assert instance.get("status") == "running"

        # 4. Verify log redirection and robust startup header
        # Give it a moment to write to logs
        await asyncio.sleep(1)
        resp = await client.get("/api/instances/default/logs?type=cache")
        assert resp.status == 200
        log_text = await resp.text()

        # Verify our new robust startup markers are present
        assert "--- Starting Squid at" in log_text
        assert "Command:" in log_text
        assert "squid.conf" in log_text

        # Verify fake_squid actually started
        assert "Fake Squid starting on port 3128" in log_text


@pytest.mark.asyncio
async def test_new_instances_running_concurrently(app_with_manager):
    """Test that multiple new instances can be started and run concurrently."""
    async with TestClient(TestServer(app_with_manager)) as client:
        instances = [
            {"name": "proxy-alpha", "port": 31130},
            {"name": "proxy-beta", "port": 31131},
        ]

        for inst in instances:
            # Create
            resp = await client.post("/api/instances", json=inst)
            assert resp.status == 201

            # Start
            resp = await client.post(f"/api/instances/{inst['name']}/start")
            assert resp.status == 200

        # Wait for all instances to write their startup logs
        await asyncio.sleep(1)

        # Verify all are running
        resp = await client.get("/api/instances")
        data = await resp.json()

        for inst in instances:
            found = next((i for i in data["instances"] if i["name"] == inst["name"]), None)
            assert found is not None, f"Instance {inst['name']} not found in API response: {data}"

            if not found.get("running"):
                # Get logs to see why it's not running
                resp_logs = await client.get(f"/api/instances/{inst['name']}/logs?type=cache")
                log_text = await resp_logs.text()
                pytest.fail(
                    f"Instance {inst['name']} is NOT running. Status: {found.get('status')}. Logs:\n{log_text}"
                )

            assert found.get("running") is True
            assert found.get("port") == inst.get("port")

            # Verify logs for each
            resp_logs = await client.get(f"/api/instances/{inst['name']}/logs?type=cache")
            log_text = await resp_logs.text()
            assert f"port {inst['port']}" in log_text
            assert "--- Starting Squid" in log_text


@pytest.mark.asyncio
async def test_instance_auto_initialization_from_config(temp_data_dir, squid_installed):
    """Test that instances defined in options.json are automatically created (simulating main.py startup)."""
    import main
    from proxy_manager import ProxyInstanceManager

    # 1. Setup options.json
    options = {
        "instances": [
            {"name": "auto-1", "port": 3140, "https_enabled": False},
            {"name": "auto-2", "port": 3141, "https_enabled": False},
        ]
    }
    options_path = temp_data_dir / "options.json"
    options_path.write_text(json.dumps(options))

    config_dir = temp_data_dir / "squid_proxy_manager"
    config_dir.mkdir(parents=True, exist_ok=True)
    certs_dir = config_dir / "certs"
    logs_dir = config_dir / "logs"
    certs_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    # 2. Initialize Manager and simulate main.py startup logic
    from unittest.mock import patch

    with patch("proxy_manager.DATA_DIR", temp_data_dir), patch(
        "proxy_manager.CONFIG_DIR", config_dir
    ), patch("proxy_manager.CERTS_DIR", certs_dir), patch(
        "proxy_manager.LOGS_DIR", logs_dir
    ), patch(
        "proxy_manager.SQUID_BINARY", squid_installed
    ), patch(
        "main.CONFIG_PATH", options_path
    ):
        manager = ProxyInstanceManager()
        main.manager = manager

        # Simulate the startup loop in main()
        config = await main.get_config()
        for inst_config in config.get("instances", []):
            await manager.create_instance(
                name=inst_config["name"],
                port=inst_config["port"],
                https_enabled=inst_config["https_enabled"],
            )
            await manager.start_instance(inst_config["name"])

        # 3. Verify both are running
        instances = await manager.get_instances()
        assert len(instances) == 2
        assert all(i["running"] for i in instances)
        assert any(i["name"] == "auto-1" and i["port"] == 3140 for i in instances)
        assert any(i["name"] == "auto-2" and i["port"] == 3141 for i in instances)

        # Cleanup
        for i in instances:
            await manager.stop_instance(i["name"])
        main.manager = None
