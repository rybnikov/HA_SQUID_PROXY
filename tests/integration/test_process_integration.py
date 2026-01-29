"""Integration tests for process-based Squid management.

These tests verify that Squid instances are correctly started as OS processes,
configuration files are generated, and cleanup works as expected.
"""
import asyncio
import socket

import pytest


@pytest.mark.asyncio
async def test_squid_process_lifecycle(proxy_manager, test_instance_name, test_port):
    """Test creating, starting, and stopping a Squid process."""
    # 1. Create instance (this also starts it)
    instance = await proxy_manager.create_instance(
        name=test_instance_name, port=test_port, https_enabled=False
    )

    assert instance["status"] == "running"
    assert test_instance_name in proxy_manager.processes

    process = proxy_manager.processes[test_instance_name]
    assert process.poll() is None, "Process should be running"

    # 2. Verify port is listening
    # Give it a moment to bind
    await asyncio.sleep(1)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Connect to localhost on the test port
        result = s.connect_ex(("127.0.0.1", test_port))
        assert result == 0, f"Port {test_port} should be listening"

    # 3. Stop instance
    success = await proxy_manager.stop_instance(test_instance_name)
    assert success is True
    assert test_instance_name not in proxy_manager.processes

    # 4. Verify port is no longer listening
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(("127.0.0.1", test_port))
        assert result != 0, f"Port {test_port} should no longer be listening"


@pytest.mark.asyncio
async def test_is_directory_error_cleanup(
    proxy_manager, test_instance_name, test_port, temp_data_dir
):
    """Test that leftover directories from Docker mounts are cleaned up."""
    instance_dir = temp_data_dir / "squid_proxy_manager" / test_instance_name
    instance_dir.mkdir(parents=True, exist_ok=True)

    # Simulate a problematic directory created by Docker volume mount
    problematic_dir = instance_dir / "squid.conf"
    problematic_dir.mkdir()
    assert problematic_dir.is_dir()

    # This should now succeed because of the cleanup logic in ProxyInstanceManager
    instance = await proxy_manager.create_instance(name=test_instance_name, port=test_port)

    assert instance["status"] == "running"
    assert (
        instance_dir / "squid.conf"
    ).is_file(), "Problematic directory should be replaced by a file"


@pytest.mark.asyncio
async def test_multiple_instances(proxy_manager):
    """Test running multiple Squid instances simultaneously."""
    instances_data = [
        {"name": "proxy1", "port": 28001},
        {"name": "proxy2", "port": 28002},
    ]

    for data in instances_data:
        await proxy_manager.create_instance(name=data["name"], port=data["port"])

    # Give them a moment to bind
    await asyncio.sleep(2)

    instances = await proxy_manager.get_instances()
    assert len(instances) == 2

    running_names = [i["name"] for i in instances if i["running"]]
    assert "proxy1" in running_names
    assert "proxy2" in running_names

    # Verify both ports
    for data in instances_data:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            assert s.connect_ex(("127.0.0.1", data["port"])) == 0


@pytest.mark.asyncio
async def test_remove_instance_cleanup(proxy_manager, test_instance_name, test_port, temp_data_dir):
    """Test that removing an instance cleans up files."""
    await proxy_manager.create_instance(name=test_instance_name, port=test_port)

    instance_dir = temp_data_dir / "squid_proxy_manager" / test_instance_name
    assert instance_dir.exists()

    await proxy_manager.remove_instance(test_instance_name)
    assert not instance_dir.exists(), "Instance directory should be deleted"
    assert test_instance_name not in proxy_manager.processes
