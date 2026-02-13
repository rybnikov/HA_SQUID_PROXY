"""Unit tests for auth_middleware in main.py.

These tests verify the authentication middleware behavior, specifically
the v1.6.2 ingress auth bypass fix.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../squid_proxy_manager/rootfs/app"))

# Mock environment variables before importing main
os.environ["SUPERVISOR_TOKEN"] = "test-token-12345"


@pytest.fixture
def mock_request():
    """Create a mock aiohttp request."""
    request = MagicMock()
    request.path = "/api/instances"
    request.method = "GET"
    request.headers = {}
    request.cookies = {}  # Mock cookies dict for auth middleware
    return request


@pytest.fixture
def mock_handler():
    """Create a mock request handler."""
    handler = AsyncMock()
    handler.return_value = web.json_response({"status": "ok"})
    return handler


class TestAuthMiddleware:
    """Tests for auth_middleware - regression tests for v1.6.2 ingress bypass."""

    @pytest.mark.asyncio
    async def test_ingress_bypass_with_x_ingress_path_header(self, mock_request, mock_handler):
        """Requests with X-Ingress-Path header should bypass auth (v1.6.2 fix)."""
        # Bug: v1.6.1 and earlier blocked all requests with 401
        # Fix: v1.6.2 checks for X-Ingress-Path header and skips auth
        from main import auth_middleware

        mock_request.headers = {"X-Ingress-Path": "/api/d0b1e7e4_squid-proxy-manager/api/instances"}

        response = await auth_middleware(mock_request, mock_handler)

        # Should call handler without checking Authorization header
        mock_handler.assert_called_once_with(mock_request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_ingress_bypass_with_x_hassio_key_header(self, mock_request, mock_handler):
        """Requests with X-Hassio-Key header should bypass auth."""
        from main import auth_middleware

        mock_request.headers = {"X-Hassio-Key": "some-hassio-key"}

        response = await auth_middleware(mock_request, mock_handler)

        # Should call handler without checking Authorization header
        mock_handler.assert_called_once_with(mock_request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_ingress_bypass_with_both_headers(self, mock_request, mock_handler):
        """Requests with both ingress headers should bypass auth."""
        from main import auth_middleware

        mock_request.headers = {
            "X-Ingress-Path": "/api/addon/api/instances",
            "X-Hassio-Key": "some-key",
        }

        response = await auth_middleware(mock_request, mock_handler)

        mock_handler.assert_called_once_with(mock_request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_non_ingress_request_requires_auth(self, mock_request, mock_handler):
        """Requests without ingress headers should require Authorization."""
        from main import auth_middleware

        # No X-Ingress-Path or X-Hassio-Key, no Authorization header
        mock_request.headers = {}

        response = await auth_middleware(mock_request, mock_handler)

        # Should NOT call handler, should return 401
        mock_handler.assert_not_called()
        assert response.status == 401
        data = response.body
        # Response should be JSON with error message
        assert b"Unauthorized" in data or b"Bearer" in data

    @pytest.mark.asyncio
    async def test_non_ingress_request_with_valid_token(self, mock_request, mock_handler):
        """Requests with valid Bearer token should succeed."""
        from main import auth_middleware

        mock_request.headers = {"Authorization": "Bearer test-token-12345"}

        response = await auth_middleware(mock_request, mock_handler)

        # Should call handler when valid token provided
        mock_handler.assert_called_once_with(mock_request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_non_ingress_request_with_invalid_token(self, mock_request, mock_handler):
        """Requests with invalid Bearer token should be rejected."""
        from main import auth_middleware

        mock_request.headers = {"Authorization": "Bearer wrong-token"}

        response = await auth_middleware(mock_request, mock_handler)

        # Should NOT call handler with wrong token
        mock_handler.assert_not_called()
        assert response.status == 401

    @pytest.mark.asyncio
    async def test_options_request_bypasses_auth(self, mock_request, mock_handler):
        """OPTIONS requests should bypass auth (CORS preflight)."""
        from main import auth_middleware

        mock_request.method = "OPTIONS"
        mock_request.headers = {}  # No auth headers

        response = await auth_middleware(mock_request, mock_handler)

        # OPTIONS should always pass through
        mock_handler.assert_called_once_with(mock_request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_non_api_path_bypasses_auth(self, mock_request, mock_handler):
        """Requests to non-/api/ paths should bypass auth middleware."""
        from main import auth_middleware

        mock_request.path = "/health"
        mock_request.headers = {}  # No auth headers

        response = await auth_middleware(mock_request, mock_handler)

        # Non-API paths should pass through
        mock_handler.assert_called_once_with(mock_request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_ingress_header_with_different_value(self, mock_request, mock_handler):
        """X-Ingress-Path with any non-empty value should bypass auth."""
        from main import auth_middleware

        # Test with a different ingress path format
        mock_request.headers = {"X-Ingress-Path": "/homeassistant/api/addon/api/instances"}

        response = await auth_middleware(mock_request, mock_handler)

        # Any X-Ingress-Path value should bypass auth
        mock_handler.assert_called_once_with(mock_request)
        assert response.status == 200


class TestAuthMiddlewareEdgeCases:
    """Edge cases for auth middleware."""

    @pytest.mark.asyncio
    async def test_empty_x_ingress_path_value(self, mock_request, mock_handler):
        """Empty X-Ingress-Path value should still bypass auth."""
        from main import auth_middleware

        mock_request.headers = {"X-Ingress-Path": ""}

        response = await auth_middleware(mock_request, mock_handler)

        # Header exists (even if empty), should bypass
        mock_handler.assert_called_once_with(mock_request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_whitespace_only_x_ingress_path(self, mock_request, mock_handler):
        """Whitespace-only X-Ingress-Path should still bypass auth."""
        from main import auth_middleware

        mock_request.headers = {"X-Ingress-Path": "   "}

        response = await auth_middleware(mock_request, mock_handler)

        # Header exists, should bypass
        mock_handler.assert_called_once_with(mock_request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_authorization_header_ignored_when_ingress_present(
        self, mock_request, mock_handler
    ):
        """When X-Ingress-Path present, Authorization header should be ignored."""
        from main import auth_middleware

        mock_request.headers = {
            "X-Ingress-Path": "/api/addon/instances",
            "Authorization": "Bearer wrong-token",  # Wrong token, but should be ignored
        }

        response = await auth_middleware(mock_request, mock_handler)

        # Should succeed because ingress header present (auth check skipped)
        mock_handler.assert_called_once_with(mock_request)
        assert response.status == 200
