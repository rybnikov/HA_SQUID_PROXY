"""Integration tests for API endpoints."""
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app"))


# Mock ProxyInstanceManager before importing main
@pytest.fixture(autouse=True)
def mock_manager_global():
    """Mock ProxyInstanceManager globally before importing main."""
    with patch("proxy_manager.ProxyInstanceManager") as mock_class:
        mock_instance = MagicMock()
        mock_instance.get_instances = AsyncMock(return_value=[])
        mock_instance.create_instance = AsyncMock(return_value={"name": "test", "status": "running"})
        mock_instance.start_instance = AsyncMock(return_value=True)
        mock_instance.stop_instance = AsyncMock(return_value=True)
        mock_instance.remove_instance = AsyncMock(return_value=True)
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_manager(mock_manager_global):
    """Mock ProxyInstanceManager."""
    return mock_manager_global


@pytest.fixture
def temp_config_file(temp_dir):
    """Create temporary config file."""
    config_file = temp_dir / "options.json"
    config_file.write_text(json.dumps({"instances": [], "log_level": "info"}))
    return config_file


@pytest.mark.asyncio
async def test_health_check(mock_manager_global):
    """Test health check endpoint."""
    # Re-import main to get the mocked manager
    import importlib
    import main
    importlib.reload(main)
    
    request = make_mocked_request("GET", "/health")
    response = await main.health_check(request)
    
    assert response.status == 200
    data = json.loads(response.text)
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_get_instances(mock_manager_global):
    """Test GET /api/instances endpoint."""
    import importlib
    import main
    importlib.reload(main)
    
    request = make_mocked_request("GET", "/api/instances")
    response = await main.get_instances(request)
    
    assert response.status == 200
    data = json.loads(response.text)
    assert "instances" in data
    mock_manager_global.get_instances.assert_called_once()


@pytest.mark.asyncio
async def test_create_instance(mock_manager_global):
    """Test POST /api/instances endpoint."""
    import importlib
    import main
    importlib.reload(main)
    
    instance_data = {
        "name": "test-instance",
        "port": 3128,
        "https_enabled": False,
        "users": [],
    }
    
    # Mock request.json()
    async def mock_json():
        return instance_data
    
    request = make_mocked_request("POST", "/api/instances")
    request.json = mock_json
    
    response = await main.create_instance(request)
    
    assert response.status == 201
    data = json.loads(response.text)
    assert data["status"] == "created"
    mock_manager_global.create_instance.assert_called_once()


@pytest.mark.asyncio
async def test_create_instance_missing_name(mock_manager_global):
    """Test POST /api/instances with missing name."""
    import importlib
    import main
    importlib.reload(main)
    
    async def mock_json():
        return {}
    
    request = make_mocked_request("POST", "/api/instances")
    request.json = mock_json
    
    response = await main.create_instance(request)
    
    assert response.status == 400
    data = json.loads(response.text)
    assert "error" in data


@pytest.mark.asyncio
async def test_start_instance(mock_manager_global):
    """Test POST /api/instances/{name}/start endpoint."""
    import importlib
    import main
    importlib.reload(main)
    
    # Create a mock request with match_info
    class MockMatchInfo:
        def get(self, key, default=None):
            return {"name": "test"}.get(key, default)
    
    request = make_mocked_request("POST", "/api/instances/test/start")
    request.match_info = MockMatchInfo()
    
    response = await main.start_instance(request)
    
    assert response.status == 200
    data = json.loads(response.text)
    assert data["status"] == "started"
    mock_manager_global.start_instance.assert_called_once_with("test")


@pytest.mark.asyncio
async def test_stop_instance(mock_manager_global):
    """Test POST /api/instances/{name}/stop endpoint."""
    import importlib
    import main
    importlib.reload(main)
    
    # Create a mock request with match_info
    class MockMatchInfo:
        def get(self, key, default=None):
            return {"name": "test"}.get(key, default)
    
    request = make_mocked_request("POST", "/api/instances/test/stop")
    request.match_info = MockMatchInfo()
    
    response = await main.stop_instance(request)
    
    assert response.status == 200
    data = json.loads(response.text)
    assert data["status"] == "stopped"
    mock_manager_global.stop_instance.assert_called_once_with("test")


@pytest.mark.asyncio
async def test_remove_instance(mock_manager_global):
    """Test DELETE /api/instances/{name} endpoint."""
    import importlib
    import main
    importlib.reload(main)
    
    # Create a mock request with match_info
    class MockMatchInfo:
        def get(self, key, default=None):
            return {"name": "test"}.get(key, default)
    
    request = make_mocked_request("DELETE", "/api/instances/test")
    request.match_info = MockMatchInfo()
    
    response = await main.remove_instance(request)
    
    assert response.status == 200
    data = json.loads(response.text)
    assert data["status"] == "removed"
    mock_manager_global.remove_instance.assert_called_once_with("test")
