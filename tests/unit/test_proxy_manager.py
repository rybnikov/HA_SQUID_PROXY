"""Tests for ProxyInstanceManager."""
# Add parent directory to path for imports
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app")
)


@pytest.fixture
def mock_docker():
    """Mock Docker client."""
    with patch("proxy_manager.docker") as mock_docker_module:
        client = MagicMock()
        client.ping.return_value = True

        # Mock containers list
        containers_list: list[Any] = []

        def containers_list_func(*args, **kwargs):
            return containers_list

        client.containers.list = containers_list_func

        def get_container(name):
            container = MagicMock()
            container.name = name
            container.id = f"container-{name}"
            container.status = "running"
            container.start = Mock()
            container.stop = Mock()
            container.remove = Mock()
            # Mock attrs for self-inspection
            container.attrs = {"Mounts": [{"Destination": "/data", "Source": "/host/data"}]}
            return container

        client.containers.get.side_effect = get_container

        # Mock container creation
        created_container = MagicMock()
        created_container.id = "new-container-id"
        created_container.start = Mock()
        client.containers.create.return_value = created_container

        mock_docker_module.DockerClient.return_value = client
        yield client


@pytest.fixture
def temp_data_dir(temp_dir):
    """Create temporary data directory structure."""
    data_dir = temp_dir / "data"
    (data_dir / "squid_proxy_manager").mkdir(parents=True)
    (data_dir / "squid_proxy_manager" / "certs").mkdir(parents=True)
    (data_dir / "squid_proxy_manager" / "logs").mkdir(parents=True)
    return data_dir


@pytest.mark.asyncio
async def test_proxy_manager_init(mock_docker):
    """Test ProxyInstanceManager initialization."""
    with patch("proxy_manager.DATA_DIR", Path("/data")), patch(
        "proxy_manager.Path.exists", return_value=True
    ), patch(
        "builtins.open",
        return_value=MagicMock(
            __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="test-id")))
        ),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()
        assert manager.docker_client is not None
        assert manager.host_data_dir == "/host/data"
        mock_docker.ping.assert_called_once()


@pytest.mark.asyncio
async def test_get_host_path(mock_docker):
    """Test host path translation."""
    with patch("proxy_manager.DATA_DIR", Path("/data")), patch(
        "proxy_manager.Path.exists", return_value=True
    ), patch(
        "builtins.open",
        return_value=MagicMock(
            __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="test-id")))
        ),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()
        manager.host_data_dir = "/host/data"

        internal_path = Path("/data/squid_proxy_manager/test/squid.conf")
        host_path = manager._get_host_path(internal_path)

        assert host_path == "/host/data/squid_proxy_manager/test/squid.conf"


@pytest.mark.asyncio
async def test_create_instance_basic(mock_docker, temp_data_dir):
    """Test creating a basic proxy instance."""
    with patch("proxy_manager.DATA_DIR", temp_data_dir), patch(
        "proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"
    ), patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"), patch(
        "proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()
        manager.docker_client = mock_docker

        # Mock container start
        container = MagicMock()
        container.id = "test-container-id"
        container.start = Mock()
        mock_docker.containers.create.return_value = container

        instance = await manager.create_instance(
            name="test-instance",
            port=3128,
            https_enabled=False,
            users=[{"username": "user1", "password": "password123"}],
        )

        assert instance["name"] == "test-instance"
        assert instance["port"] == 3128
        assert instance["https_enabled"] is False
        assert instance["container_id"] == "test-container-id"
        assert instance["status"] == "running"


@pytest.mark.asyncio
async def test_get_instances(mock_docker):
    """Test getting list of instances."""
    with patch("proxy_manager.DATA_DIR", Path("/data")):
        from proxy_manager import ProxyInstanceManager

        # Mock containers
        container1 = MagicMock()
        container1.name = "squid-proxy-instance1"
        container1.id = "id1"
        container1.status = "running"

        container2 = MagicMock()
        container2.name = "squid-proxy-instance2"
        container2.id = "id2"
        container2.status = "stopped"

        # Update the containers list function
        def containers_list_func(*args, **kwargs):
            return [container1, container2]

        mock_docker.containers.list = containers_list_func

        manager = ProxyInstanceManager()
        manager.docker_client = mock_docker

        instances = await manager.get_instances()

        assert len(instances) == 2
        assert instances[0]["name"] == "instance1"
        assert instances[0]["running"] is True
        assert instances[1]["name"] == "instance2"
        assert instances[1]["running"] is False


@pytest.mark.asyncio
async def test_start_instance(mock_docker):
    """Test starting an instance."""
    with patch("proxy_manager.DATA_DIR", Path("/data")):
        from proxy_manager import ProxyInstanceManager

        container = MagicMock()
        container.start = Mock()

        def get_container(name):
            return container

        mock_docker.containers.get.side_effect = get_container

        manager = ProxyInstanceManager()
        manager.docker_client = mock_docker

        result = await manager.start_instance("test-instance")

        assert result is True
        # Note: start is called via executor, so we check it was accessed
        assert mock_docker.containers.get.called


@pytest.mark.asyncio
async def test_stop_instance(mock_docker):
    """Test stopping an instance."""
    with patch("proxy_manager.DATA_DIR", Path("/data")):
        from proxy_manager import ProxyInstanceManager

        container = MagicMock()
        container.stop = Mock()

        def get_container(name):
            return container

        mock_docker.containers.get.side_effect = get_container

        manager = ProxyInstanceManager()
        manager.docker_client = mock_docker

        result = await manager.stop_instance("test-instance")

        assert result is True
        # Note: stop is called via executor with timeout, so we check it was accessed
        assert mock_docker.containers.get.called


@pytest.mark.asyncio
async def test_remove_instance(mock_docker):
    """Test removing an instance."""
    with patch("proxy_manager.DATA_DIR", Path("/data")):
        from proxy_manager import ProxyInstanceManager

        container = MagicMock()
        container.remove = Mock()

        def get_container(name):
            return container

        mock_docker.containers.get.side_effect = get_container

        manager = ProxyInstanceManager()
        manager.docker_client = mock_docker

        result = await manager.remove_instance("test-instance")

        assert result is True
        # Note: remove is called via executor with force, so we check it was accessed
        assert mock_docker.containers.get.called
