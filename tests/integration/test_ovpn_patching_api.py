"""Integration tests for OpenVPN config patching API endpoint."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import FormData
from aiohttp.test_utils import make_mocked_request

# Add parent directory to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app")
)

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "sample_ovpn"


@pytest.fixture
def basic_ovpn_content():
    """Load basic OpenVPN config content."""
    return (FIXTURES_DIR / "basic_client.ovpn").read_text()


@pytest.fixture
def tls_tunnel_ovpn_content():
    """Load TLS tunnel OpenVPN config content."""
    return (FIXTURES_DIR / "tls_tunnel_config.ovpn").read_text()


@pytest.fixture
def mock_manager():
    """Create mock ProxyInstanceManager."""
    manager = MagicMock()
    manager.list_instances = MagicMock(
        return_value=[
            {
                "name": "squid-proxy",
                "port": 3128,
                "proxy_type": "squid",
                "external_ip": "192.168.1.100",
            },
            {
                "name": "tls-tunnel",
                "port": 4443,
                "proxy_type": "tls_tunnel",
                "external_ip": "10.0.0.50",
            },
        ]
    )
    manager.update_instance = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_app(mock_manager):
    """Create mock aiohttp application."""
    app = MagicMock()
    app.__getitem__ = lambda self, key: mock_manager if key == "manager" else None
    return app


class TestPatchOVPNSquidInstance:
    """Tests for patching .ovpn for Squid instances."""

    @pytest.mark.asyncio
    async def test_patch_ovpn_squid_instance_no_auth(
        self, basic_ovpn_content, mock_app, mock_manager
    ):
        """Upload .ovpn to Squid instance without auth, verify response."""
        # Import main after mocking
        import importlib

        import main

        importlib.reload(main)

        # Create multipart form data
        form = FormData()
        form.add_field(
            "file", basic_ovpn_content, filename="client.ovpn", content_type="text/plain"
        )

        # Create mock request with multipart reader
        request = make_mocked_request(
            "POST",
            "/api/instances/squid-proxy/patch-ovpn",
            app=mock_app,
            match_info={"name": "squid-proxy"},
        )

        # Mock multipart reader
        async def mock_multipart_gen():
            """Mock multipart reader that yields file content."""
            parts = []

            class FilePart:
                name = "file"

                async def read(self):
                    return basic_ovpn_content.encode("utf-8")

            parts.append(FilePart())

            for part in parts:
                yield part

        async def mock_multipart():
            return mock_multipart_gen()

        request.multipart = mock_multipart  # type: ignore[method-assign]

        # Call endpoint
        response = await main.patch_ovpn_config(request)

        # Verify response
        assert response.status == 200
        data = json.loads(response.text)
        assert "patched_content" in data
        assert "filename" in data
        assert data["filename"] == "squid-proxy_patched.ovpn"

        # Verify patched content includes proxy settings
        patched = data["patched_content"]
        assert "http-proxy 192.168.1.100 3128" in patched
        assert "<http-proxy-user-pass>" not in patched

    @pytest.mark.asyncio
    async def test_patch_ovpn_squid_with_auth(self, basic_ovpn_content, mock_app, mock_manager):
        """Upload .ovpn with username/password, verify auth block added."""
        import importlib

        import main

        importlib.reload(main)

        request = make_mocked_request(
            "POST",
            "/api/instances/squid-proxy/patch-ovpn",
            app=mock_app,
            match_info={"name": "squid-proxy"},
        )

        # Mock multipart reader with auth credentials
        async def mock_multipart_gen():
            class FilePart:
                name = "file"

                async def read(self):
                    return basic_ovpn_content.encode("utf-8")

            class UsernamePart:
                name = "username"

                async def text(self):
                    return "testuser"

            class PasswordPart:
                name = "password"

                async def text(self):
                    return "testpass"

            yield FilePart()
            yield UsernamePart()
            yield PasswordPart()

        async def mock_multipart():
            return mock_multipart_gen()

        request.multipart = mock_multipart  # type: ignore[method-assign]

        response = await main.patch_ovpn_config(request)

        assert response.status == 200
        data = json.loads(response.text)
        patched = data["patched_content"]

        # Verify auth block present
        assert "http-proxy 192.168.1.100 3128" in patched
        assert "<http-proxy-user-pass>" in patched
        assert "testuser" in patched
        assert "testpass" in patched
        assert "</http-proxy-user-pass>" in patched

    @pytest.mark.asyncio
    async def test_patch_ovpn_with_external_ip(self, basic_ovpn_content, mock_app, mock_manager):
        """Upload .ovpn with custom external_host parameter."""
        import importlib

        import main

        importlib.reload(main)

        request = make_mocked_request(
            "POST",
            "/api/instances/squid-proxy/patch-ovpn",
            app=mock_app,
            match_info={"name": "squid-proxy"},
        )

        async def mock_multipart_gen():
            class FilePart:
                name = "file"

                async def read(self):
                    return basic_ovpn_content.encode("utf-8")

            class ExternalHostPart:
                name = "external_host"

                async def text(self):
                    return "custom.proxy.com"

            yield FilePart()
            yield ExternalHostPart()

        async def mock_multipart():
            return mock_multipart_gen()

        request.multipart = mock_multipart  # type: ignore[method-assign]

        response = await main.patch_ovpn_config(request)

        assert response.status == 200
        data = json.loads(response.text)
        patched = data["patched_content"]

        # Should use custom external_host instead of instance external_ip
        assert "http-proxy custom.proxy.com 3128" in patched


class TestPatchOVPNTLSTunnelInstance:
    """Tests for patching .ovpn for TLS Tunnel instances."""

    @pytest.mark.asyncio
    async def test_patch_ovpn_tls_tunnel_instance(
        self, tls_tunnel_ovpn_content, mock_app, mock_manager
    ):
        """Upload .ovpn to TLS tunnel, verify VPN server extracted."""
        import importlib

        import main

        importlib.reload(main)

        request = make_mocked_request(
            "POST",
            "/api/instances/tls-tunnel/patch-ovpn",
            app=mock_app,
            match_info={"name": "tls-tunnel"},
        )

        async def mock_multipart_gen():
            class FilePart:
                name = "file"

                async def read(self):
                    return tls_tunnel_ovpn_content.encode("utf-8")

            yield FilePart()

        async def mock_multipart():
            return mock_multipart_gen()

        request.multipart = mock_multipart  # type: ignore[method-assign]

        response = await main.patch_ovpn_config(request)

        assert response.status == 200
        data = json.loads(response.text)
        patched = data["patched_content"]

        # Verify remote directive replaced
        assert "remote 10.0.0.50 4443" in patched
        assert "vpn-server.example.org" not in patched

        # Verify update_instance called with extracted VPN server
        mock_manager.update_instance.assert_called_once_with(
            "tls-tunnel", forward_address="vpn-server.example.org:443"
        )

    @pytest.mark.asyncio
    async def test_patch_ovpn_updates_tls_tunnel_forward_address(
        self, tls_tunnel_ovpn_content, mock_app, mock_manager
    ):
        """Verify instance metadata updated with extracted VPN server."""
        import importlib

        import main

        importlib.reload(main)

        request = make_mocked_request(
            "POST",
            "/api/instances/tls-tunnel/patch-ovpn",
            app=mock_app,
            match_info={"name": "tls-tunnel"},
        )

        async def mock_multipart_gen():
            class FilePart:
                name = "file"

                async def read(self):
                    return tls_tunnel_ovpn_content.encode("utf-8")

            yield FilePart()

        async def mock_multipart():
            return mock_multipart_gen()

        request.multipart = mock_multipart  # type: ignore[method-assign]

        await main.patch_ovpn_config(request)

        # Verify forward_address updated
        mock_manager.update_instance.assert_called_once()
        call_args = mock_manager.update_instance.call_args
        assert call_args[0][0] == "tls-tunnel"
        assert call_args[1]["forward_address"] == "vpn-server.example.org:443"


class TestPatchOVPNErrorHandling:
    """Tests for error handling in patch_ovpn_config endpoint."""

    @pytest.mark.asyncio
    async def test_patch_ovpn_invalid_file(self, mock_app):
        """Upload non-.ovpn file, expect 400."""
        import importlib

        import main

        importlib.reload(main)

        request = make_mocked_request(
            "POST",
            "/api/instances/squid-proxy/patch-ovpn",
            app=mock_app,
            match_info={"name": "squid-proxy"},
        )

        async def mock_multipart_gen():
            class FilePart:
                name = "file"

                async def read(self):
                    return b"This is not a valid OpenVPN config"

            yield FilePart()

        async def mock_multipart():
            return mock_multipart_gen()

        request.multipart = mock_multipart  # type: ignore[method-assign]

        response = await main.patch_ovpn_config(request)

        assert response.status == 400
        data = json.loads(response.text)
        assert "error" in data
        assert "valid OpenVPN config" in data["error"]

    @pytest.mark.asyncio
    async def test_patch_ovpn_file_too_large(self, mock_app):
        """Upload oversized file, expect 400."""
        import importlib

        import main

        importlib.reload(main)

        request = make_mocked_request(
            "POST",
            "/api/instances/squid-proxy/patch-ovpn",
            app=mock_app,
            match_info={"name": "squid-proxy"},
        )

        # Create file larger than 1MB
        large_content = "a" * (1024 * 1024 + 1)

        async def mock_multipart_gen():
            class FilePart:
                name = "file"

                async def read(self):
                    return large_content.encode("utf-8")

            yield FilePart()

        async def mock_multipart():
            return mock_multipart_gen()

        request.multipart = mock_multipart  # type: ignore[method-assign]

        response = await main.patch_ovpn_config(request)

        assert response.status == 400
        data = json.loads(response.text)
        assert "error" in data
        assert "too large" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_patch_ovpn_empty_file(self, mock_app):
        """Upload empty file, expect 400."""
        import importlib

        import main

        importlib.reload(main)

        request = make_mocked_request(
            "POST",
            "/api/instances/squid-proxy/patch-ovpn",
            app=mock_app,
            match_info={"name": "squid-proxy"},
        )

        async def mock_multipart_gen():
            class FilePart:
                name = "file"

                async def read(self):
                    return b""

            yield FilePart()

        async def mock_multipart():
            return mock_multipart_gen()

        request.multipart = mock_multipart  # type: ignore[method-assign]

        response = await main.patch_ovpn_config(request)

        assert response.status == 400
        data = json.loads(response.text)
        assert "error" in data
        assert "no file uploaded" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_patch_ovpn_nonexistent_instance(self, mock_app, mock_manager):
        """Upload to invalid instance, expect 404."""
        import importlib

        import main

        importlib.reload(main)

        # Configure mock to return empty list for nonexistent instance
        mock_manager.list_instances.return_value = []

        request = make_mocked_request(
            "POST",
            "/api/instances/nonexistent/patch-ovpn",
            app=mock_app,
            match_info={"name": "nonexistent"},
        )

        basic_content = "client\ndev tun\nremote test.com 1194\n"

        async def mock_multipart_gen():
            class FilePart:
                name = "file"

                async def read(self):
                    return basic_content.encode("utf-8")

            yield FilePart()

        async def mock_multipart():
            return mock_multipart_gen()

        request.multipart = mock_multipart  # type: ignore[method-assign]

        response = await main.patch_ovpn_config(request)

        assert response.status == 404
        data = json.loads(response.text)
        assert "error" in data
        assert "not found" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_patch_ovpn_no_file_uploaded(self, mock_app):
        """Request without file upload, expect 400."""
        import importlib

        import main

        importlib.reload(main)

        request = make_mocked_request(
            "POST",
            "/api/instances/squid-proxy/patch-ovpn",
            app=mock_app,
            match_info={"name": "squid-proxy"},
        )

        # Mock multipart with no file part
        async def mock_multipart_gen():
            class UsernamePart:
                name = "username"

                async def text(self):
                    return "testuser"

            yield UsernamePart()

        async def mock_multipart():
            return mock_multipart_gen()

        request.multipart = mock_multipart  # type: ignore[method-assign]

        response = await main.patch_ovpn_config(request)

        assert response.status == 400
        data = json.loads(response.text)
        assert "error" in data
        assert "no file" in data["error"].lower()


class TestPatchOVPNFallbackBehavior:
    """Tests for fallback behavior in patch_ovpn_config endpoint."""

    @pytest.mark.asyncio
    async def test_patch_ovpn_no_external_ip_uses_localhost(
        self, basic_ovpn_content, mock_app, mock_manager
    ):
        """Instance without external_ip should default to localhost."""
        import importlib

        import main

        importlib.reload(main)

        # Configure instance without external_ip
        mock_manager.list_instances.return_value = [
            {
                "name": "squid-proxy",
                "port": 3128,
                "proxy_type": "squid",
                # No external_ip
            }
        ]

        request = make_mocked_request(
            "POST",
            "/api/instances/squid-proxy/patch-ovpn",
            app=mock_app,
            match_info={"name": "squid-proxy"},
        )

        async def mock_multipart_gen():
            class FilePart:
                name = "file"

                async def read(self):
                    return basic_ovpn_content.encode("utf-8")

            yield FilePart()

        async def mock_multipart():
            return mock_multipart_gen()

        request.multipart = mock_multipart  # type: ignore[method-assign]

        response = await main.patch_ovpn_config(request)

        assert response.status == 200
        data = json.loads(response.text)
        patched = data["patched_content"]

        # Should default to localhost
        assert "http-proxy localhost 3128" in patched
