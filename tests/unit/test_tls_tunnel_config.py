"""Unit tests for TlsTunnelConfigGenerator."""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app")
)

from tls_tunnel_config import TlsTunnelConfigGenerator, validate_forward_address

# ---------------------------------------------------------------------------
# validate_forward_address tests
# ---------------------------------------------------------------------------


class TestValidateForwardAddress:
    """Tests for the validate_forward_address() helper."""

    def test_valid_hostname_port(self):
        """Valid host:port should not raise."""
        validate_forward_address("vpn.example.com:1194")

    def test_valid_ip_port(self):
        """IP:port should not raise."""
        validate_forward_address("192.168.1.1:443")

    def test_valid_short_hostname(self):
        """Single-word hostname with port should not raise."""
        validate_forward_address("localhost:8080")

    def test_valid_boundary_port_low(self):
        """Port 1 is the lowest valid port."""
        validate_forward_address("host:1")

    def test_valid_boundary_port_high(self):
        """Port 65535 is the highest valid port."""
        validate_forward_address("host:65535")

    def test_invalid_missing_port(self):
        """Missing port should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid forward address"):
            validate_forward_address("vpn.example.com")

    def test_invalid_empty_string(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid forward address"):
            validate_forward_address("")

    def test_invalid_port_zero(self):
        """Port 0 should raise ValueError."""
        with pytest.raises(ValueError, match="Port out of range"):
            validate_forward_address("host:0")

    def test_invalid_port_above_65535(self):
        """Port above 65535 should raise ValueError."""
        with pytest.raises(ValueError, match="Port out of range"):
            validate_forward_address("host:65536")

    def test_invalid_port_not_a_number(self):
        """Non-numeric port should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid forward address"):
            validate_forward_address("host:abc")

    def test_invalid_spaces_in_hostname(self):
        """Spaces in hostname should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid forward address"):
            validate_forward_address("my host:1194")

    def test_invalid_special_chars(self):
        """Special characters (e.g. /) should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid forward address"):
            validate_forward_address("host/path:1194")


# ---------------------------------------------------------------------------
# TlsTunnelConfigGenerator.generate_stream_config tests
# ---------------------------------------------------------------------------


class TestGenerateStreamConfig:
    """Tests for generate_stream_config()."""

    def test_stream_config_content(self):
        """Verify nginx stream config contains expected directives."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "nginx_stream.conf"
            gen = TlsTunnelConfigGenerator("my-tunnel", 8443, "vpn.example.com:1194", 18443)
            gen.generate_stream_config(config_file)

            assert config_file.exists()
            content = config_file.read_text()

            assert "ssl_preread on" in content
            assert "listen 8443" in content
            assert 'vpn.example.com:1194;' in content
            assert "127.0.0.1:18443" in content
            assert "proxy_connect_timeout 5s" in content
            assert "proxy_timeout 86400s" in content
            assert "load_module" in content
            assert "ngx_stream_module" in content

    def test_stream_config_safe_name_sanitization(self):
        """Hyphens and special chars in instance name are replaced by underscores in identifiers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "nginx_stream.conf"
            gen = TlsTunnelConfigGenerator("my-tunnel.v2", 8443, "vpn.example.com:1194", 18443)
            gen.generate_stream_config(config_file)

            content = config_file.read_text()
            # '-' and '.' replaced with '_'
            assert "$backend_my_tunnel_v2" in content
            assert "map $ssl_preread_protocol $backend_my_tunnel_v2" in content

    def test_stream_config_file_permissions(self):
        """Config file should have 0640 permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "nginx_stream.conf"
            gen = TlsTunnelConfigGenerator("test", 8443, "vpn.example.com:1194", 18443)
            gen.generate_stream_config(config_file)

            assert oct(config_file.stat().st_mode)[-3:] == "640"

    def test_stream_config_different_ports(self):
        """Verify different port values are reflected in config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for listen_port, cover_port in [(443, 10443), (8443, 18443), (9999, 19999)]:
                config_file = Path(tmpdir) / f"stream_{listen_port}.conf"
                gen = TlsTunnelConfigGenerator("tunnel", listen_port, "vpn:1194", cover_port)
                gen.generate_stream_config(config_file)

                content = config_file.read_text()
                assert f"listen {listen_port}" in content
                assert f"127.0.0.1:{cover_port}" in content


# ---------------------------------------------------------------------------
# TlsTunnelConfigGenerator.generate_cover_site_config tests
# ---------------------------------------------------------------------------


class TestGenerateCoverSiteConfig:
    """Tests for generate_cover_site_config()."""

    def test_cover_site_config_content(self):
        """Verify nginx HTTP config for cover site contains expected directives."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            config_file = Path(tmpdir) / "nginx_cover.conf"
            gen = TlsTunnelConfigGenerator(
                "my-tunnel",
                8443,
                "vpn.example.com:1194",
                18443,
                data_dir=str(data_dir),
            )
            gen.generate_cover_site_config(
                config_file,
                cert_path="/certs/cover.crt",
                key_path="/certs/cover.key",
                server_name="mysite.example.com",
            )

            assert config_file.exists()
            content = config_file.read_text()

            assert "listen 127.0.0.1:18443 ssl" in content
            assert "server_name mysite.example.com" in content
            assert "ssl_certificate /certs/cover.crt" in content
            assert "ssl_certificate_key /certs/cover.key" in content
            assert "ssl_protocols TLSv1.2 TLSv1.3" in content
            assert "index index.html" in content
            assert "try_files" in content

    def test_cover_site_config_default_server_name(self):
        """Default server_name should be underscore (_)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            config_file = Path(tmpdir) / "nginx_cover.conf"
            gen = TlsTunnelConfigGenerator(
                "tunnel", 8443, "vpn:1194", 18443, data_dir=str(data_dir)
            )
            gen.generate_cover_site_config(config_file, cert_path="/c.crt", key_path="/c.key")

            content = config_file.read_text()
            assert "server_name _" in content

    def test_cover_site_creates_default_html(self):
        """If no index.html exists, a default one should be created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            config_file = Path(tmpdir) / "nginx_cover.conf"
            gen = TlsTunnelConfigGenerator(
                "my-tunnel", 8443, "vpn:1194", 18443, data_dir=str(data_dir)
            )
            gen.generate_cover_site_config(config_file, cert_path="/c.crt", key_path="/c.key")

            index_file = data_dir / "my-tunnel" / "cover_site" / "index.html"
            assert index_file.exists()
            html = index_file.read_text()
            assert "<!DOCTYPE html>" in html
            assert "Welcome" in html
            assert "under construction" in html

    def test_cover_site_does_not_overwrite_existing_html(self):
        """If index.html already exists, it should NOT be overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            # Pre-create custom HTML
            cover_dir = data_dir / "my-tunnel" / "cover_site"
            cover_dir.mkdir(parents=True)
            index_file = cover_dir / "index.html"
            index_file.write_text("<html>Custom</html>")

            config_file = Path(tmpdir) / "nginx_cover.conf"
            gen = TlsTunnelConfigGenerator(
                "my-tunnel", 8443, "vpn:1194", 18443, data_dir=str(data_dir)
            )
            gen.generate_cover_site_config(config_file, cert_path="/c.crt", key_path="/c.key")

            assert index_file.read_text() == "<html>Custom</html>"

    def test_cover_site_config_file_permissions(self):
        """Config file should have 0640 permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            config_file = Path(tmpdir) / "nginx_cover.conf"
            gen = TlsTunnelConfigGenerator("test", 8443, "vpn:1194", 18443, data_dir=str(data_dir))
            gen.generate_cover_site_config(config_file, cert_path="/c.crt", key_path="/c.key")

            assert oct(config_file.stat().st_mode)[-3:] == "640"


# ---------------------------------------------------------------------------
# TlsTunnelConfigGenerator._default_cover_html tests
# ---------------------------------------------------------------------------


class TestDefaultCoverHtml:
    """Tests for _default_cover_html()."""

    def test_html_structure(self):
        """Verify the default HTML has proper structure."""
        gen = TlsTunnelConfigGenerator("test", 8443, "vpn:1194", 18443)
        html = gen._default_cover_html()

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "<title>Welcome</title>" in html
        assert "under construction" in html


# ---------------------------------------------------------------------------
# TlsTunnelConfigGenerator.__init__ tests
# ---------------------------------------------------------------------------


class TestTlsTunnelConfigGeneratorInit:
    """Tests for TlsTunnelConfigGenerator initialization."""

    def test_init_stores_attributes(self):
        """Verify constructor stores all arguments."""
        gen = TlsTunnelConfigGenerator(
            "my-tunnel", 8443, "vpn.example.com:1194", 18443, "/custom/data"
        )
        assert gen.instance_name == "my-tunnel"
        assert gen.listen_port == 8443
        assert gen.forward_address == "vpn.example.com:1194"
        assert gen.cover_site_port == 18443
        assert gen.data_dir == "/custom/data"

    def test_init_default_data_dir(self):
        """Default data_dir should be /data/squid_proxy_manager."""
        gen = TlsTunnelConfigGenerator("test", 8443, "vpn:1194", 18443)
        assert gen.data_dir == "/data/squid_proxy_manager"
