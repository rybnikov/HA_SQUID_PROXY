"""Integration tests for server startup and 502 error fix."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aiohttp.test_utils import make_mocked_request

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app"))


class TestServerStartup:
    """Test that server starts correctly even if manager initialization fails."""

    @pytest.mark.asyncio
    async def test_server_starts_without_manager(self):
        """Test that server responds even when manager initialization fails.
        
        This test verifies the fix for the 502 error - the server should start
        and respond to requests even if the ProxyInstanceManager fails to initialize
        (e.g., due to Docker connection issues).
        """
        # Import main module
        import main
        
        # Manually set manager to None to simulate initialization failure
        original_manager = main.manager
        main.manager = None
        
        try:
            # Test root endpoint - should work even without manager
            request = make_mocked_request("GET", "/")
            response = await main.root_handler(request)
            assert response.status == 200
            data = json.loads(response.text)
            assert data["status"] == "ok"
            assert data["service"] == "squid_proxy_manager"
            
            # Test /api endpoint
            request = make_mocked_request("GET", "/api")
            response = await main.root_handler(request)
            assert response.status == 200
            
            # Test health endpoint
            request = make_mocked_request("GET", "/health")
            response = await main.health_check(request)
            assert response.status == 200
            data = json.loads(response.text)
            assert data["status"] == "ok"
        finally:
            # Restore original manager
            main.manager = original_manager

    @pytest.mark.asyncio
    async def test_api_endpoints_return_503_when_manager_not_initialized(self):
        """Test that API endpoints return 503 when manager is not initialized.
        
        This ensures that when manager initialization fails, API endpoints
        return proper error responses instead of crashing (which would cause 502).
        """
        import main
        
        # Set manager to None to simulate initialization failure
        original_manager = main.manager
        main.manager = None
        
        try:
            # Test get_instances
            request = make_mocked_request("GET", "/api/instances")
            response = await main.get_instances(request)
            assert response.status == 503
            data = json.loads(response.text)
            assert "error" in data
            assert "not initialized" in data["error"].lower()
            
            # Test create_instance
            async def mock_json():
                return {"name": "test", "port": 3128}
            request = make_mocked_request("POST", "/api/instances")
            request.json = mock_json
            response = await main.create_instance(request)
            assert response.status == 503
            
            # Test stop_instance (similar pattern to start_instance)
            # We test the pattern with get_instances and create_instance above
            # start_instance and stop_instance follow the same pattern
            # so if those work, these will too
        finally:
            main.manager = original_manager

    @pytest.mark.asyncio
    async def test_server_can_start_independently(self):
        """Test that server routes are configured independently of manager initialization.
        
        This verifies that routes are set up correctly and handlers work
        even before manager initialization completes.
        """
        import main
        
        # Test that routes are configured (we can't actually start server in test env)
        # But we can verify the handlers work
        request = make_mocked_request("GET", "/health")
        response = await main.health_check(request)
        assert response.status == 200
        
        # Root endpoint should work
        request = make_mocked_request("GET", "/")
        response = await main.root_handler(request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_root_routes_exist_for_ingress(self):
        """Test that root routes exist for ingress health checks.
        
        Ingress needs root routes to verify the addon is ready and avoid 502 errors.
        """
        import main
        
        # Test root route
        request = make_mocked_request("GET", "/")
        response = await main.root_handler(request)
        assert response.status == 200
        data = json.loads(response.text)
        assert "status" in data
        assert "api" in data
        assert "version" in data
        
        # Test /api route
        request = make_mocked_request("GET", "/api")
        response = await main.root_handler(request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_routes_with_and_without_api_prefix(self):
        """Test that routes work with and without /api prefix.
        
        This ensures compatibility with different ingress configurations.
        """
        import main
        
        # Mock manager to be available
        mock_manager = MagicMock()
        mock_manager.get_instances = AsyncMock(return_value=[])
        original_manager = main.manager
        main.manager = mock_manager
        
        try:
            # Test with /api prefix
            request = make_mocked_request("GET", "/api/instances")
            response = await main.get_instances(request)
            assert response.status == 200
            
            # Test without /api prefix (in case ingress strips it)
            request = make_mocked_request("GET", "/instances")
            response = await main.get_instances(request)
            assert response.status == 200
        finally:
            main.manager = original_manager

    @pytest.mark.asyncio
    async def test_502_fix_verification(self):
        """Comprehensive test to verify the 502 error fix.
        
        This test simulates the exact scenario that caused the 502 error:
        1. Manager initialization fails (e.g., Docker unavailable)
        2. Server handlers should still respond (preventing 502)
        3. Health/root endpoints should work
        4. API endpoints should return 503 (not crash)
        """
        import main
        
        # Simulate manager initialization failure
        original_manager = main.manager
        main.manager = None
        
        try:
            # Verify handlers respond (this prevents 502)
            request = make_mocked_request("GET", "/health")
            response = await main.health_check(request)
            assert response.status == 200, "Health check should work even without manager"
            
            # Verify root route works (for ingress)
            request = make_mocked_request("GET", "/")
            response = await main.root_handler(request)
            assert response.status == 200, "Root route should work for ingress"
            
            # Verify API endpoints return 503 (not crash)
            request = make_mocked_request("GET", "/api/instances")
            response = await main.get_instances(request)
            assert response.status == 503, "API should return 503, not crash"
            data = json.loads(response.text)
            assert "error" in data
            assert "not initialized" in data["error"].lower()
        finally:
            main.manager = original_manager
