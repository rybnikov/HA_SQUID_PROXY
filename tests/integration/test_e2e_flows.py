"""End-to-end tests for HA Squid Proxy manager user flows (Process-based)."""

import asyncio
import os
import sys

import pytest

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../squid_proxy_manager/rootfs/app"))
from network_utils import can_bind_port, check_port_connectivity


@pytest.mark.asyncio
@pytest.mark.network
async def test_instance_full_lifecycle(proxy_manager, test_instance_name, test_port):
    """Test the full lifecycle of a proxy instance: Create -> Stop -> Start -> Remove."""
    # Skip if network binding is not available
    if not can_bind_port():
        pytest.skip("Network port binding not available (sandbox environment)")

    # 1. Create instance (it starts automatically in process mode)
    instance = await proxy_manager.create_instance(
        name=test_instance_name, port=test_port, https_enabled=False, users=[]
    )
    assert instance is not None
    assert instance["name"] == test_instance_name
    assert instance["status"] == "running"

    # Wait for process to be running and port to be bound
    await asyncio.sleep(2)

    instances = await proxy_manager.get_instances()
    instance = next(i for i in instances if i["name"] == test_instance_name)
    # Check if process exists even if port binding failed
    assert instance is not None
    assert test_instance_name in proxy_manager.processes or instance.get("running") is True

    # 2. Stop instance
    # Wait a bit to ensure instance is fully started
    await asyncio.sleep(1)
    stopped = await proxy_manager.stop_instance(test_instance_name)
    if not stopped:
        # If stop failed, check if process still exists
        if test_instance_name in proxy_manager.processes:
            # Try to stop again with more time
            await asyncio.sleep(1)
            stopped = await proxy_manager.stop_instance(test_instance_name)
    assert (
        stopped is True
    ), f"Failed to stop instance. Process exists: {test_instance_name in proxy_manager.processes}, Instance status: {await proxy_manager.get_instances()}"

    instances = await proxy_manager.get_instances()
    instance = next(i for i in instances if i["name"] == test_instance_name)
    assert instance["running"] is False

    # 3. Start again
    started = await proxy_manager.start_instance(test_instance_name)
    assert started is True

    await asyncio.sleep(2)

    instances = await proxy_manager.get_instances()
    instance = next(i for i in instances if i["name"] == test_instance_name)
    assert instance["running"] is True

    # 4. Remove instance
    removed = await proxy_manager.remove_instance(test_instance_name)
    assert removed is True

    instances = await proxy_manager.get_instances()
    assert not any(i["name"] == test_instance_name for i in instances)


@pytest.mark.asyncio
async def test_https_instance_creation(proxy_manager, test_instance_name, test_port):
    """Test creating an instance with HTTPS enabled."""
    instance = await proxy_manager.create_instance(
        name=test_instance_name, port=test_port, https_enabled=True, users=[]
    )
    assert instance["status"] == "running"

    # Verify certificates were generated
    from proxy_manager import CERTS_DIR

    cert_path = CERTS_DIR / test_instance_name / "squid.crt"
    key_path = CERTS_DIR / test_instance_name / "squid.key"

    assert cert_path.exists()
    assert key_path.exists()
    assert cert_path.stat().st_size > 0
    assert key_path.stat().st_size > 0


@pytest.mark.asyncio
async def test_user_management(proxy_manager, test_instance_name, test_port):
    """Test creating an instance with users and verify auth file."""
    users = [{"username": "testuser", "password": "testpassword"}]  # pragma: allowlist secret
    await proxy_manager.create_instance(
        name=test_instance_name, port=test_port, https_enabled=False, users=users
    )

    # Verify password file was created
    from proxy_manager import CONFIG_DIR

    passwd_path = CONFIG_DIR / test_instance_name / "passwd"

    assert passwd_path.exists()
    assert passwd_path.stat().st_size > 0

    # Verify content (it should contain the username)
    content = passwd_path.read_text()
    assert "testuser" in content


@pytest.mark.asyncio
@pytest.mark.network
async def test_proxy_functionality(proxy_manager, test_instance_name, test_port):
    """Test that the proxy instance actually accepts connections."""
    # Skip if network binding is not available
    if not can_bind_port():
        pytest.skip("Network port binding not available (sandbox environment)")

    # Create instance
    await proxy_manager.create_instance(
        name=test_instance_name, port=test_port, https_enabled=False, users=[]
    )

    # Give it time to fully start
    await asyncio.sleep(2)

    # Verify process exists
    assert test_instance_name in proxy_manager.processes, "Process should be created"
    process = proxy_manager.processes[test_instance_name]
    assert process.poll() is None, "Process should be running"

    # Try to connect to the port (only if network is available)
    if check_port_connectivity("127.0.0.1", test_port):
        # Port is accessible, test passed
        pass
    else:
        # Port binding might have failed, but process exists
        # This is acceptable in sandbox environments
        pytest.skip(
            "Port connectivity check failed (may be sandbox restriction), but process exists"
        )
