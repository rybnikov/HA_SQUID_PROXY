"""End-to-end tests for HA Squid Proxy manager user flows (Process-based)."""
import asyncio
import os
import socket
import sys

import pytest

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../squid_proxy_manager/rootfs/app"))


@pytest.mark.asyncio
async def test_instance_full_lifecycle(proxy_manager, test_instance_name, test_port):
    """Test the full lifecycle of a proxy instance: Create -> Stop -> Start -> Remove."""
    # 1. Create instance (it starts automatically in process mode)
    instance = await proxy_manager.create_instance(
        name=test_instance_name, port=test_port, https_enabled=False, users=[]
    )
    assert instance is not None
    assert instance["name"] == test_instance_name
    assert instance["status"] == "running"

    # Wait for process to be running and port to be bound
    await asyncio.sleep(1)

    instances = await proxy_manager.get_instances()
    instance = next(i for i in instances if i["name"] == test_instance_name)
    assert instance["running"] is True

    # 2. Stop instance
    stopped = await proxy_manager.stop_instance(test_instance_name)
    assert stopped is True

    instances = await proxy_manager.get_instances()
    instance = next(i for i in instances if i["name"] == test_instance_name)
    assert instance["running"] is False

    # 3. Start again
    started = await proxy_manager.start_instance(test_instance_name)
    assert started is True

    await asyncio.sleep(1)

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

    cert_path = CERTS_DIR / test_instance_name / "proxyCA.pem"
    key_path = CERTS_DIR / test_instance_name / "proxyCA.key"

    assert cert_path.exists()
    assert key_path.exists()
    assert cert_path.stat().st_size > 0
    assert key_path.stat().st_size > 0


@pytest.mark.asyncio
async def test_user_management(proxy_manager, test_instance_name, test_port):
    """Test creating an instance with users and verify auth file."""
    users = [{"username": "testuser", "password": "testpassword"}]
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
async def test_proxy_functionality(proxy_manager, test_instance_name, test_port):
    """Test that the proxy instance actually accepts connections."""
    # Create instance
    await proxy_manager.create_instance(
        name=test_instance_name, port=test_port, https_enabled=False, users=[]
    )

    # Give it time to fully start
    await asyncio.sleep(1)

    # Try to connect to the port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(("127.0.0.1", test_port))
        assert result == 0, f"Port {test_port} should be listening"
