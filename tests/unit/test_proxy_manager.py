"""Unit tests for ProxyInstanceManager using process-based architecture."""

# Add parent directory to path for imports
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app")
)


@pytest.fixture
def mock_popen():
    """Mock subprocess.Popen."""
    with patch("subprocess.Popen") as mock_popen_class:
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Running
        mock_popen_class.return_value = mock_process
        yield mock_popen_class


@pytest.fixture
def temp_data_dir(temp_dir):
    """Create temporary data directory structure."""
    data_dir = temp_dir / "data"
    (data_dir / "squid_proxy_manager").mkdir(parents=True)
    (data_dir / "squid_proxy_manager" / "certs").mkdir(parents=True)
    (data_dir / "squid_proxy_manager" / "logs").mkdir(parents=True)
    return data_dir


@pytest.mark.asyncio
async def test_proxy_manager_init(temp_data_dir):
    """Test ProxyInstanceManager initialization."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()
        assert manager.processes == {}
        assert (temp_data_dir / "squid_proxy_manager").exists()


@pytest.mark.asyncio
async def test_create_instance_basic(mock_popen, temp_data_dir):
    """Test creating a basic proxy instance."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
        patch("os.path.exists", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        instance = await manager.create_instance(
            name="test-instance",
            port=3128,
            https_enabled=False,
            users=[{"username": "user1", "password": "password123"}],
        )

        assert instance["name"] == "test-instance"
        assert instance["port"] == 3128
        assert instance["status"] == "running"
        assert "test-instance" in manager.processes
        mock_popen.assert_called_once()
        # Should call subprocess.run for cache initialization (-z)
        mock_run.assert_called()


@pytest.mark.asyncio
async def test_get_instances(mock_popen, temp_data_dir):
    """Test getting list of instances."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        # Create a dummy instance directory
        instance_dir = temp_data_dir / "squid_proxy_manager" / "instance1"
        instance_dir.mkdir(parents=True)
        (instance_dir / "squid.conf").touch()

        # Mock a running process
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        manager.processes["instance1"] = mock_process

        instances = await manager.get_instances()

        assert len(instances) == 1
        assert instances[0]["name"] == "instance1"
        assert instances[0]["running"] is True


@pytest.mark.asyncio
async def test_start_instance(mock_popen, temp_data_dir):
    """Test starting an instance."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
        patch("os.path.exists", return_value=True),
        patch("subprocess.run"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        # Create config file
        instance_dir = temp_data_dir / "squid_proxy_manager" / "test-instance"
        instance_dir.mkdir(parents=True)
        (instance_dir / "squid.conf").touch()

        result = await manager.start_instance("test-instance")

        assert result is True
        assert "test-instance" in manager.processes
        mock_popen.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_instance(temp_data_dir):
        """Test stopping an instance."""
        with (
            patch("proxy_manager.DATA_DIR", temp_data_dir),
            patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
            patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
            patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
            patch("os.killpg") as mock_killpg,
            patch("os.getpgid", return_value=123),
        ):
            from proxy_manager import ProxyInstanceManager

            manager = ProxyInstanceManager()

            mock_process = MagicMock()
            mock_process.pid = 12345
            # First poll returns None (running), second returns 0 (stopped)
            mock_process.poll.side_effect = [None, 0]
            manager.processes["test-instance"] = mock_process

            result = await manager.stop_instance("test-instance")

            assert result is True
            assert "test-instance" not in manager.processes
            mock_killpg.assert_called_once()


@pytest.mark.asyncio
async def test_remove_instance(temp_data_dir):
    """Test removing an instance."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        # Create instance directory
        instance_dir = temp_data_dir / "squid_proxy_manager" / "test-instance"
        instance_dir.mkdir(parents=True)

        result = await manager.remove_instance("test-instance")

        assert result is True
        assert not instance_dir.exists()
