"""Unit tests for OpenVPN config patcher module."""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app")
)

from ovpn_patcher import (
    patch_ovpn_for_squid,
    patch_ovpn_for_tls_tunnel,
    validate_ovpn_content,
)

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "sample_ovpn"


@pytest.fixture
def basic_ovpn():
    """Load basic OpenVPN config fixture."""
    return (FIXTURES_DIR / "basic_client.ovpn").read_text()


@pytest.fixture
def ovpn_with_comments():
    """Load OpenVPN config with comments fixture."""
    return (FIXTURES_DIR / "with_comments.ovpn").read_text()


@pytest.fixture
def tls_tunnel_ovpn():
    """Load TLS tunnel OpenVPN config fixture."""
    return (FIXTURES_DIR / "tls_tunnel_config.ovpn").read_text()


@pytest.fixture
def no_remote_ovpn():
    """Load OpenVPN config without remote directive."""
    return (FIXTURES_DIR / "no_remote.ovpn").read_text()


class TestValidateOVPNContent:
    """Tests for validate_ovpn_content() function."""

    def test_validate_ovpn_content_valid(self, basic_ovpn):
        """Valid .ovpn file should pass validation."""
        is_valid, error_msg = validate_ovpn_content(basic_ovpn)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_ovpn_content_valid_with_comments(self, ovpn_with_comments):
        """Valid .ovpn file with comments should pass validation."""
        is_valid, error_msg = validate_ovpn_content(ovpn_with_comments)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_ovpn_content_empty(self):
        """Empty file should fail validation."""
        is_valid, error_msg = validate_ovpn_content("")
        assert is_valid is False
        assert "empty" in error_msg.lower()

    def test_validate_ovpn_content_whitespace_only(self):
        """File with only whitespace should fail validation."""
        is_valid, error_msg = validate_ovpn_content("   \n\n  \t  ")
        assert is_valid is False
        assert "empty" in error_msg.lower()

    def test_validate_ovpn_content_too_large(self):
        """File larger than 1MB should fail validation."""
        large_content = "a" * (1024 * 1024 + 1)
        is_valid, error_msg = validate_ovpn_content(large_content)
        assert is_valid is False
        assert "too large" in error_msg.lower()

    def test_validate_ovpn_content_invalid_structure(self):
        """File without recognized OpenVPN directives should fail."""
        invalid_content = "This is not an OpenVPN config\njust some random text\n"
        is_valid, error_msg = validate_ovpn_content(invalid_content)
        assert is_valid is False
        assert "valid OpenVPN config" in error_msg

    def test_validate_ovpn_content_only_comments(self):
        """File with only comments should fail validation."""
        comments_only = "# Comment 1\n# Comment 2\n# Comment 3\n"
        is_valid, error_msg = validate_ovpn_content(comments_only)
        assert is_valid is False
        assert "valid OpenVPN config" in error_msg


class TestPatchOVPNForSquid:
    """Tests for patch_ovpn_for_squid() function."""

    def test_patch_ovpn_for_squid_no_auth(self, basic_ovpn):
        """Squid patching without auth should add http-proxy directive."""
        patched = patch_ovpn_for_squid(basic_ovpn, proxy_host="192.168.1.100", proxy_port=3128)

        assert "http-proxy 192.168.1.100 3128" in patched
        assert "<http-proxy-user-pass>" not in patched
        # Verify original content preserved
        assert "client" in patched
        assert "dev tun" in patched
        assert "remote vpn.example.com 1194" in patched

    def test_patch_ovpn_for_squid_with_auth(self, basic_ovpn):
        """Squid patching with auth should add http-proxy with inline auth block."""
        patched = patch_ovpn_for_squid(
            basic_ovpn,
            proxy_host="proxy.local",
            proxy_port=8080,
            username="testuser",
            password="testpass",
        )

        assert "http-proxy proxy.local 8080" in patched
        assert "<http-proxy-user-pass>" in patched
        assert "testuser" in patched
        assert "testpass" in patched
        assert "</http-proxy-user-pass>" in patched

        # Verify auth block structure (should be together)
        lines = patched.split("\n")
        http_proxy_idx = next(i for i, line in enumerate(lines) if "http-proxy" in line)
        assert "<http-proxy-user-pass>" in lines[http_proxy_idx + 1]
        assert "testuser" in lines[http_proxy_idx + 2]
        assert "testpass" in lines[http_proxy_idx + 3]
        assert "</http-proxy-user-pass>" in lines[http_proxy_idx + 4]

    def test_patch_ovpn_for_squid_preserves_comments(self, ovpn_with_comments):
        """Squid patching should preserve comments and formatting."""
        patched = patch_ovpn_for_squid(ovpn_with_comments, proxy_host="10.0.0.1", proxy_port=3128)

        assert "http-proxy 10.0.0.1 3128" in patched
        # Verify comments preserved
        assert "# OpenVPN configuration with extensive comments" in patched
        assert "# VPN server address" in patched
        assert "# Security settings" in patched

    def test_patch_ovpn_for_squid_removes_existing_http_proxy(self):
        """Squid patching should remove existing http-proxy directives."""
        content_with_proxy = """client
dev tun
http-proxy old.proxy.com 8888
remote vpn.example.com 1194
"""
        patched = patch_ovpn_for_squid(
            content_with_proxy, proxy_host="new.proxy.com", proxy_port=3128
        )

        assert "http-proxy new.proxy.com 3128" in patched
        assert "old.proxy.com" not in patched

    def test_patch_ovpn_for_squid_no_client_directive(self):
        """Squid patching should work even without client directive."""
        content_no_client = """dev tun
proto udp
remote vpn.example.com 1194
"""
        patched = patch_ovpn_for_squid(content_no_client, proxy_host="proxy.local", proxy_port=3128)

        # Should add http-proxy at beginning if no 'client' directive
        assert "http-proxy proxy.local 3128" in patched
        lines = patched.split("\n")
        assert "http-proxy" in lines[0]

    def test_patch_ovpn_for_squid_partial_auth(self):
        """Squid patching with only username should not add auth block."""
        patched = patch_ovpn_for_squid(
            "client\ndev tun\n",
            proxy_host="proxy.local",
            proxy_port=3128,
            username="testuser",
            # No password
        )

        assert "http-proxy proxy.local 3128" in patched
        assert "<http-proxy-user-pass>" not in patched


class TestPatchOVPNForTLSTunnel:
    """Tests for patch_ovpn_for_tls_tunnel() function."""

    def test_patch_ovpn_for_tls_tunnel_extracts_vpn_server(self, tls_tunnel_ovpn):
        """TLS tunnel patching should extract VPN server address."""
        patched, vpn_server = patch_ovpn_for_tls_tunnel(
            tls_tunnel_ovpn, tunnel_host="localhost", tunnel_port=4443
        )

        assert vpn_server == "vpn-server.example.org:443"
        assert "remote localhost 4443" in patched
        assert "vpn-server.example.org" not in patched

    def test_patch_ovpn_for_tls_tunnel_replaces_remote(self, basic_ovpn):
        """TLS tunnel patching should replace remote directive."""
        patched, vpn_server = patch_ovpn_for_tls_tunnel(
            basic_ovpn, tunnel_host="127.0.0.1", tunnel_port=5000
        )

        assert vpn_server == "vpn.example.com:1194"
        assert "remote 127.0.0.1 5000" in patched
        assert "remote vpn.example.com 1194" not in patched

    def test_patch_ovpn_for_tls_tunnel_no_remote_found(self, no_remote_ovpn):
        """TLS tunnel patching should handle missing remote directive."""
        patched, vpn_server = patch_ovpn_for_tls_tunnel(
            no_remote_ovpn, tunnel_host="tunnel.local", tunnel_port=8443
        )

        # Should add remote directive
        assert "remote tunnel.local 8443" in patched
        # VPN server should be empty string when no remote found
        assert vpn_server == ""

    def test_patch_ovpn_for_tls_tunnel_default_port(self):
        """TLS tunnel should assume port 1194 if not specified in remote."""
        content = """client
dev tun
remote vpn.example.com
"""
        patched, vpn_server = patch_ovpn_for_tls_tunnel(
            content, tunnel_host="tunnel.local", tunnel_port=4443
        )

        # Should default to port 1194
        assert vpn_server == "vpn.example.com:1194"
        assert "remote tunnel.local 4443" in patched

    def test_patch_ovpn_for_tls_tunnel_preserves_other_directives(self, tls_tunnel_ovpn):
        """TLS tunnel patching should preserve all other directives."""
        patched, _ = patch_ovpn_for_tls_tunnel(
            tls_tunnel_ovpn, tunnel_host="localhost", tunnel_port=4443
        )

        # Verify other directives preserved
        assert "client" in patched
        assert "dev tun" in patched
        assert "proto tcp" in patched
        assert "cipher AES-256-GCM" in patched
        assert "auth SHA512" in patched
        assert "tls-client" in patched

    def test_patch_ovpn_for_tls_tunnel_multiple_remote_directives(self):
        """TLS tunnel should only replace first remote directive."""
        content = """client
dev tun
remote vpn1.example.com 1194
remote vpn2.example.com 1194
remote vpn3.example.com 1194
"""
        patched, vpn_server = patch_ovpn_for_tls_tunnel(
            content, tunnel_host="tunnel.local", tunnel_port=4443
        )

        # Should extract first remote
        assert vpn_server == "vpn1.example.com:1194"
        # Should replace first remote only
        assert "remote tunnel.local 4443" in patched
        # Other remotes should remain
        assert "remote vpn2.example.com 1194" in patched
        assert "remote vpn3.example.com 1194" in patched
        # First remote should not be in output
        assert "remote vpn1.example.com" not in patched
