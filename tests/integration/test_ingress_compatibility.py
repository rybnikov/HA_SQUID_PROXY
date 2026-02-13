"""Integration tests for ingress compatibility.

These tests verify that the server handles various ingress edge cases correctly,
including path normalization, multiple slashes, and proper HTTP responses.

Run with: pytest tests/integration/test_ingress_compatibility.py -v
"""

import asyncio
import os
import re
import sys
from typing import Any

import pytest
from aiohttp import web

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../squid_proxy_manager/rootfs/app"))
# Add integration tests directory to path for test_helpers
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import call_handler


class TestPathNormalizationMiddleware:
    """Test the path normalization middleware that handles ingress quirks."""

    def create_app_with_normalization(self):
        """Create a test app with path normalization middleware."""

        async def root_handler(request):
            return web.json_response({"path": "/", "handler": "root"})

        async def health_handler(request):
            return web.json_response({"status": "ok", "handler": "health"})

        async def api_instances_handler(request):
            return web.json_response({"instances": [], "handler": "api_instances"})

        @web.middleware
        async def normalize_path_middleware(request, handler):
            """Normalize multiple slashes to single slash."""
            original_path = request.path
            normalized_path = re.sub(r"/+", "/", original_path)

            if normalized_path != original_path:
                # For paths like //// -> /, serve the root handler directly
                if normalized_path == "/":
                    return await root_handler(request)

            return await handler(request)

        @web.middleware
        async def logging_middleware(request, handler):
            """Log requests for debugging."""
            try:
                response = await handler(request)
                return response
            except Exception:
                raise

        app = web.Application(middlewares=[normalize_path_middleware, logging_middleware])
        app.router.add_get("/", root_handler)
        app.router.add_get("/health", health_handler)
        app.router.add_get("/api/instances", api_instances_handler)

        return app

    @pytest.mark.asyncio
    async def test_normal_root_path(self):
        """Test normal root path /."""
        app = self.create_app_with_normalization()

        resp = await call_handler(app, "GET", "/")
        assert resp.status == 200
        data = await resp.json()
        assert data["handler"] == "root"

    @pytest.mark.asyncio
    async def test_multiple_slashes_to_root(self):
        """Test that //// is handled as root."""
        app = self.create_app_with_normalization()

        # Note: Some HTTP clients may normalize this before sending
        # But the middleware should handle it anyway
        resp = await call_handler(app, "GET", "////")
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test /health endpoint."""
        app = self.create_app_with_normalization()

        resp = await call_handler(app, "GET", "/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_api_instances_endpoint(self):
        """Test /api/instances endpoint."""
        app = self.create_app_with_normalization()

        resp = await call_handler(app, "GET", "/api/instances")
        assert resp.status == 200
        data = await resp.json()
        assert "instances" in data


class TestIngressHeaders:
    """Test handling of ingress-specific headers."""

    def create_test_app(self):
        """Create a test app that echoes request info."""

        async def echo_handler(request):
            return web.json_response(
                {
                    "path": request.path,
                    "method": request.method,
                    "headers": dict(request.headers),
                    "remote": request.remote,
                }
            )

        app = web.Application()
        app.router.add_get("/", echo_handler)
        app.router.add_get("/api/{tail:.*}", echo_handler)

        return app

    @pytest.mark.asyncio
    async def test_accept_header_html(self):
        """Test that Accept: text/html header is handled."""
        app = self.create_test_app()

        resp = await call_handler(app, "GET", "/", headers={"Accept": "text/html"})
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_accept_header_json(self):
        """Test that Accept: application/json header is handled."""
        app = self.create_test_app()

        resp = await call_handler(app, "GET", "/", headers={"Accept": "application/json"})
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_x_forwarded_headers(self):
        """Test handling of X-Forwarded-* headers from ingress."""
        app = self.create_test_app()

        resp = await call_handler(
            app,
            "GET",
            "/",
            headers={
                "X-Forwarded-For": "192.168.1.100",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "homeassistant.local:8123",
            },
        )
        assert resp.status == 200
        data = await resp.json()
        assert "X-Forwarded-For" in data["headers"]


class TestHTTPMethods:
    """Test various HTTP methods used by the API."""

    def create_api_app(self):
        """Create a test app with API endpoints."""

        instances: dict[str, dict[str, Any]] = {}

        async def get_instances(request):
            return web.json_response({"instances": list(instances.values())})

        async def create_instance(request):
            data = await request.json()
            name = data.get("name")
            if not name:
                return web.json_response({"error": "Name required"}, status=400)
            instances[name] = data
            return web.json_response({"status": "created", "instance": data}, status=201)

        async def delete_instance(request):
            name = request.match_info.get("name")
            if name in instances:
                del instances[name]
                return web.json_response({"status": "removed"})
            return web.json_response({"error": "Not found"}, status=404)

        async def start_instance(request):
            name = request.match_info.get("name")
            if name in instances:
                return web.json_response({"status": "started"})
            return web.json_response({"error": "Not found"}, status=404)

        async def stop_instance(request):
            name = request.match_info.get("name")
            if name in instances:
                return web.json_response({"status": "stopped"})
            return web.json_response({"error": "Not found"}, status=404)

        app = web.Application()
        app.router.add_get("/api/instances", get_instances)
        app.router.add_post("/api/instances", create_instance)
        app.router.add_delete("/api/instances/{name}", delete_instance)
        app.router.add_post("/api/instances/{name}/start", start_instance)
        app.router.add_post("/api/instances/{name}/stop", stop_instance)

        return app

    @pytest.mark.asyncio
    async def test_get_instances(self):
        """Test GET /api/instances."""
        app = self.create_api_app()

        resp = await call_handler(app, "GET", "/api/instances")
        assert resp.status == 200
        data = await resp.json()
        assert "instances" in data

    @pytest.mark.asyncio
    async def test_create_instance(self):
        """Test POST /api/instances."""
        app = self.create_api_app()

        resp = await call_handler(
            app, "POST", "/api/instances", json_data={"name": "test", "port": 3128}
        )
        assert resp.status == 201
        data = await resp.json()
        assert data["status"] == "created"

    @pytest.mark.asyncio
    async def test_create_instance_without_name(self):
        """Test POST /api/instances without name returns 400."""
        app = self.create_api_app()

        resp = await call_handler(app, "POST", "/api/instances", json_data={"port": 3128})
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_delete_instance(self):
        """Test DELETE /api/instances/{name}."""
        app = self.create_api_app()

        # Create first
        await call_handler(app, "POST", "/api/instances", json_data={"name": "test", "port": 3128})

        # Delete
        resp = await call_handler(app, "DELETE", "/api/instances/test")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "removed"

    @pytest.mark.asyncio
    async def test_delete_nonexistent_instance(self):
        """Test DELETE /api/instances/{name} for nonexistent instance."""
        app = self.create_api_app()

        resp = await call_handler(app, "DELETE", "/api/instances/nonexistent")
        assert resp.status == 404

    @pytest.mark.asyncio
    async def test_start_instance(self):
        """Test POST /api/instances/{name}/start."""
        app = self.create_api_app()

        # Create first
        await call_handler(app, "POST", "/api/instances", json_data={"name": "test", "port": 3128})

        # Start
        resp = await call_handler(app, "POST", "/api/instances/test/start")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "started"

    @pytest.mark.asyncio
    async def test_stop_instance(self):
        """Test POST /api/instances/{name}/stop."""
        app = self.create_api_app()

        # Create first
        await call_handler(app, "POST", "/api/instances", json_data={"name": "test", "port": 3128})

        # Stop
        resp = await call_handler(app, "POST", "/api/instances/test/stop")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "stopped"


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_404_for_unknown_route(self):
        """Test that unknown routes return 404."""
        app = web.Application()

        async def root_handler(request):
            return web.Response(text="OK")

        app.router.add_get("/", root_handler)

        resp = await call_handler(app, "GET", "/unknown/route")
        assert resp.status == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(self):
        """Test that wrong HTTP method returns 405."""
        app = web.Application()

        async def test_handler(request):
            return web.Response(text="OK")

        app.router.add_get("/api/test", test_handler)

        resp = await call_handler(app, "POST", "/api/test")
        assert resp.status == 405

    @pytest.mark.asyncio
    async def test_invalid_json_body(self):
        """Test handling of invalid JSON in request body."""

        async def handler(request):
            try:
                data = await request.json()
                return web.json_response(data)
            except Exception:
                return web.json_response({"error": "Invalid JSON"}, status=400)

        app = web.Application()
        app.router.add_post("/api/test", handler)

        # For invalid JSON, create a request and mock the json() method to raise an exception
        from aiohttp.test_utils import make_mocked_request

        request = make_mocked_request(
            "POST",
            "http://localhost/api/test",
            app=app,
            headers={"Content-Type": "application/json"},
        )

        # Mock json() to raise an exception (simulating invalid JSON)
        async def mock_json():
            raise ValueError("Invalid JSON")

        request.json = mock_json  # type: ignore[assignment,method-assign]

        # Use app._handle to process through middleware
        resp = await app._handle(request)
        assert resp.status == 400


class TestConcurrentRequests:
    """Test handling of concurrent requests."""

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Test multiple concurrent health check requests."""

        async def health_handler(request):
            await asyncio.sleep(0.01)  # Simulate some work
            return web.json_response({"status": "ok"})

        app = web.Application()
        app.router.add_get("/health", health_handler)

        # Send 10 concurrent requests
        tasks = [call_handler(app, "GET", "/health") for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for resp in responses:
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self):
        """Test multiple concurrent API requests."""

        counter = {"value": 0}

        async def increment_handler(request):
            counter["value"] += 1
            await asyncio.sleep(0.01)
            return web.json_response({"count": counter["value"]})

        app = web.Application()
        app.router.add_get("/api/count", increment_handler)

        # Send 5 concurrent requests
        tasks = [call_handler(app, "GET", "/api/count") for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for resp in responses:
            assert resp.status == 200

        # Counter should have been incremented 5 times
        assert counter["value"] == 5


class TestWebUIServing:
    """Test web UI serving for ingress."""

    @pytest.mark.asyncio
    async def test_html_response_for_browser(self):
        """Test that HTML is returned for browser requests."""

        async def root_handler(request):
            accept = request.headers.get("Accept", "")
            if "text/html" in accept:
                return web.Response(
                    text="<html><body>Web UI</body></html>", content_type="text/html"
                )
            return web.json_response({"status": "ok"})

        app = web.Application()
        app.router.add_get("/", root_handler)

        # Browser request
        resp = await call_handler(app, "GET", "/", headers={"Accept": "text/html,*/*"})
        assert resp.status == 200
        assert "text/html" in resp.content_type

        # API request
        resp = await call_handler(app, "GET", "/", headers={"Accept": "application/json"})
        assert resp.status == 200
        assert "application/json" in resp.content_type


class TestIngressAuthBypass:
    """Integration tests for ingress authentication bypass (v1.6.2 regression tests)."""

    @pytest.mark.asyncio
    async def test_ingress_request_bypasses_auth_middleware(self):
        """Requests with X-Ingress-Path header should bypass authentication.

        This is a regression test for v1.6.2 critical bug where desktop browsers
        received 401 errors when accessing through HA ingress.
        """
        import os
        import sys

        # Mock supervisor token
        os.environ["SUPERVISOR_TOKEN"] = "test-integration-token-123"

        # Add app to path
        sys.path.insert(
            0, os.path.join(os.path.dirname(__file__), "../../squid_proxy_manager/rootfs/app")
        )
        from main import auth_middleware

        @web.middleware
        async def auth_mw(request, handler):
            return await auth_middleware(request, handler)

        async def test_handler(request):
            return web.json_response({"data": "success"})

        app = web.Application(middlewares=[auth_mw])
        app.router.add_get("/api/instances", test_handler)

        # Test with X-Ingress-Path header (should bypass auth and succeed)
        resp = await call_handler(
            app,
            "GET",
            "/api/instances",
            headers={"X-Ingress-Path": "/api/hassio_ingress/test-addon/api/instances"},
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["data"] == "success"

    @pytest.mark.asyncio
    async def test_x_hassio_key_header_bypasses_auth(self):
        """Requests with X-Hassio-Key header should also bypass authentication."""
        import os
        import sys

        os.environ["SUPERVISOR_TOKEN"] = "test-token-789"

        sys.path.insert(
            0, os.path.join(os.path.dirname(__file__), "../../squid_proxy_manager/rootfs/app")
        )
        from main import auth_middleware

        @web.middleware
        async def auth_mw(request, handler):
            return await auth_middleware(request, handler)

        async def test_handler(request):
            return web.json_response({"data": "success"})

        app = web.Application(middlewares=[auth_mw])
        app.router.add_get("/api/instances", test_handler)

        # Test with X-Hassio-Key header (alternative ingress indicator)
        resp = await call_handler(
            app, "GET", "/api/instances", headers={"X-Hassio-Key": "some-hassio-key-value"}
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["data"] == "success"
