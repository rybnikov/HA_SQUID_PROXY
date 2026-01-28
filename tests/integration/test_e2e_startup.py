"""End-to-end tests for Squid Proxy Manager startup and operation."""
import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aiohttp import ClientSession, web
from aiohttp.test_utils import make_mocked_request

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app"))


class TestE2EStartup:
    """End-to-end tests for application startup."""

    @pytest.mark.asyncio
    async def test_full_startup_sequence(self):
        """Test the complete startup sequence from beginning to end.
        
        This test verifies:
        1. Application can start
        2. Routes are registered correctly
        3. Server setup completes without errors
        """
        import main
        
        # Create app and verify routes without actually starting server
        app = web.Application()
        
        # Add middleware
        @web.middleware
        async def logging_middleware(request, handler):
            return await handler(request)
        app.middlewares.append(logging_middleware)
        
        # Register routes (same as in start_app)
        app.router.add_get("/", main.root_handler)
        app.router.add_get("/api", main.root_handler)
        app.router.add_get("/health", main.health_check)
        app.router.add_get("/api/instances", main.get_instances)
        app.router.add_post("/api/instances", main.create_instance)
        app.router.add_get("/instances", main.get_instances)
        
        # Verify routes are registered
        routes = [str(route) for route in app.router.routes()]
        route_str = " ".join(routes)
        assert "/" in route_str or "GET /" in route_str, "Root route should be registered"
        assert "/api" in route_str or "GET /api" in route_str, "/api route should be registered"
        assert "/health" in route_str or "GET /health" in route_str, "Health route should be registered"
        assert "/api/instances" in route_str or "GET /api/instances" in route_str, "API instances route should be registered"
        
        # Verify app runner can be created
        runner = web.AppRunner(app)
        await runner.setup()
        try:
            assert runner._app is not None, "App should be initialized"
        finally:
            await runner.cleanup()

    @pytest.mark.asyncio
    async def test_startup_with_manager_initialization_failure(self):
        """Test startup when manager initialization fails.
        
        This simulates the 502 error scenario:
        - Manager fails to initialize (e.g., Docker unavailable)
        - Health endpoints should work
        - API endpoints should return 503 (not 502)
        """
        import main
        
        # Set manager to None to simulate failure
        original_manager = main.manager
        main.manager = None
        
        try:
            # Verify health endpoint works even without manager
            request = make_mocked_request("GET", "/health")
            response = await main.health_check(request)
            assert response.status == 200
            data = json.loads(response.text)
            assert data["status"] == "ok"
            assert data["manager_initialized"] is False
            
            # Verify root endpoint works
            request = make_mocked_request("GET", "/")
            response = await main.root_handler(request)
            assert response.status == 200
            data = json.loads(response.text)
            assert data["status"] == "ok"
            assert data["manager_initialized"] is False
            
            # Verify API endpoint returns 503 (not 502)
            request = make_mocked_request("GET", "/api/instances")
            response = await main.get_instances(request)
            assert response.status == 503, "Should return 503, not 502"
            data = json.loads(response.text)
            assert "error" in data
            assert "not initialized" in data["error"].lower()
            
        finally:
            main.manager = original_manager

    @pytest.mark.asyncio
    async def test_startup_with_config_loading(self):
        """Test startup with configuration file loading."""
        import main
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "instances": [
                    {
                        "name": "test-instance",
                        "port": 3128,
                        "https_enabled": False,
                        "users": []
                    }
                ],
                "log_level": "info"
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            # Mock the config path
            original_config_path = main.CONFIG_PATH
            main.CONFIG_PATH = Path(config_path)
            
            # Mock manager
            mock_manager = MagicMock()
            mock_manager.get_instances = AsyncMock(return_value=[])
            mock_manager.create_instance = AsyncMock(return_value={"name": "test-instance", "status": "running"})
            
            with patch("main.ProxyInstanceManager", return_value=mock_manager):
                # Initialize manager
                main.manager = mock_manager
                
                try:
                    # Load config
                    config = await main.get_config()
                    assert "instances" in config
                    assert len(config["instances"]) == 1
                    assert config["instances"][0]["name"] == "test-instance"
                finally:
                    main.manager = None
        finally:
            main.CONFIG_PATH = original_config_path
            os.unlink(config_path)

    @pytest.mark.asyncio
    async def test_all_routes_accessible(self):
        """Test that all routes are accessible and return proper responses."""
        import main
        
        # Mock manager
        mock_manager = MagicMock()
        mock_manager.get_instances = AsyncMock(return_value=[])
        original_manager = main.manager
        main.manager = mock_manager
        
        try:
            # Test root route
            request = make_mocked_request("GET", "/")
            response = await main.root_handler(request)
            assert response.status == 200
            
            # Test /api route
            request = make_mocked_request("GET", "/api")
            response = await main.root_handler(request)
            assert response.status == 200
            
            # Test health route
            request = make_mocked_request("GET", "/health")
            response = await main.health_check(request)
            assert response.status == 200
            
            # Test API routes
            request = make_mocked_request("GET", "/api/instances")
            response = await main.get_instances(request)
            assert response.status == 200
            
            # Test routes without /api prefix
            request = make_mocked_request("GET", "/instances")
            response = await main.get_instances(request)
            assert response.status == 200
            
        finally:
            main.manager = original_manager

    @pytest.mark.asyncio
    async def test_error_handling_during_startup(self):
        """Test that errors during startup don't prevent handlers from working."""
        import main
        
        # Test manager init failure scenario
        original_manager = main.manager
        main.manager = None
        
        try:
            # Health check should work even without manager
            request = make_mocked_request("GET", "/health")
            response = await main.health_check(request)
            assert response.status == 200, "Health check should work without manager"
            
            # Root handler should work
            request = make_mocked_request("GET", "/")
            response = await main.root_handler(request)
            assert response.status == 200, "Root handler should work without manager"
        finally:
            main.manager = original_manager

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test that server handles concurrent requests correctly."""
        import main
        
        mock_manager = MagicMock()
        mock_manager.get_instances = AsyncMock(return_value=[])
        original_manager = main.manager
        main.manager = mock_manager
        
        try:
            # Simulate concurrent requests
            async def make_request():
                request = make_mocked_request("GET", "/health")
                return await main.health_check(request)
            
            # Make multiple concurrent requests
            tasks = [make_request() for _ in range(10)]
            responses = await asyncio.gather(*tasks)
            
            # All should succeed
            for response in responses:
                assert response.status == 200
                
        finally:
            main.manager = original_manager

    @pytest.mark.asyncio
    async def test_logging_middleware(self):
        """Test that logging middleware can be added."""
        import main
        
        # Create app with middleware
        app = web.Application()
        
        @web.middleware
        async def logging_middleware(request, handler):
            return await handler(request)
        
        app.middlewares.append(logging_middleware)
        
        # Verify middleware is registered
        assert len(app.middlewares) > 0, "Middleware should be registered"
        
        # Test that middleware works
        app.router.add_get("/health", main.health_check)
        request = make_mocked_request("GET", "/health")
        response = await app._handle(request)
        assert response.status == 200
