"""Tests for SquidConfigGenerator."""

# Add parent directory to path for imports
import sys
import tempfile
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app")
)

from squid_config import SquidConfigGenerator


def test_squid_config_generator_init():
    """Test SquidConfigGenerator initialization."""
    gen = SquidConfigGenerator("test-instance", 3128, False)
    assert gen.instance_name == "test-instance"
    assert gen.port == 3128
    assert gen.https_enabled is False


def test_generate_config_basic():
    """Test generating basic Squid configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        data_dir = "/data/squid_proxy_manager"
        gen = SquidConfigGenerator("test-instance", 3128, False, data_dir)
        gen.generate_config(config_file)

        assert config_file.exists()
        content = config_file.read_text()

        # Check basic settings
        assert "http_port 3128" in content
        assert "test-instance" in content
        assert "auth_param basic" in content
        assert f"{data_dir}/test-instance/passwd" in content

        # Check permissions
        assert oct(config_file.stat().st_mode)[-3:] == "640"


def test_generate_config_https():
    """Test generating Squid configuration with HTTPS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        data_dir = "/data/squid_proxy_manager"
        gen = SquidConfigGenerator("test-instance", 8080, True, data_dir)
        gen.generate_config(config_file)

        assert config_file.exists()
        content = config_file.read_text()

        # Check HTTPS settings - no ssl_bump (causes signing cert requirement), no quotes on paths
        assert "https_port 8080" in content
        assert "ssl_bump" not in content  # ssl_bump was removed to fix HTTPS
        assert f"tls-cert={data_dir}/certs/test-instance/squid.crt" in content
        assert f"tls-key={data_dir}/certs/test-instance/squid.key" in content
        # Squid 6.13+ dropped the `options` keyword for https_port.
        assert "options=" not in content


def test_generate_config_security_hardening():
    """Test that security hardening directives are included."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        gen = SquidConfigGenerator("test-instance", 3128, False)
        gen.generate_config(config_file)

        content = config_file.read_text()

        # Check security hardening
        assert "via off" in content
        assert "forwarded_for delete" in content
        assert "cache deny all" in content
        assert "request_header_access X-Forwarded-For deny all" in content


def test_generate_config_different_ports():
    """Test generating configs with different ports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        for port in [3128, 8080, 8888, 9999]:
            config_file = Path(tmpdir) / f"squid_{port}.conf"
            gen = SquidConfigGenerator("test-instance", port, False)
            gen.generate_config(config_file)

            content = config_file.read_text()
            assert f"http_port {port}" in content


def test_generate_config_custom_data_dir():
    """Test generating config with custom data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        custom_data_dir = "/custom/path"
        gen = SquidConfigGenerator("my-proxy", 3130, False, custom_data_dir)
        gen.generate_config(config_file)

        content = config_file.read_text()

        # Verify custom paths are used
        assert f"{custom_data_dir}/my-proxy/passwd" in content
        assert f"{custom_data_dir}/logs/my-proxy/access.log" in content
        assert f"{custom_data_dir}/logs/my-proxy/cache.log" in content


def test_generate_config_dpi_prevention_enabled():
    """Test generating config with DPI prevention enabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        gen = SquidConfigGenerator("dpi-proxy", 3128, False, dpi_prevention=True)
        gen.generate_config(config_file)

        content = config_file.read_text()

        # DPI prevention directives must be present
        assert "httpd_suppress_version_string on" in content
        assert "visible_hostname localhost" in content
        assert "request_header_access Proxy-Connection deny all" in content
        assert "request_header_access Surrogate-Capability deny all" in content
        assert "follow_x_forwarded_for deny all" in content
        assert "reply_header_access X-Cache deny all" in content
        assert "reply_header_access X-Cache-Lookup deny all" in content
        assert "reply_header_access X-Squid-Error deny all" in content
        assert "client_persistent_connections on" in content
        assert "server_persistent_connections on" in content
        assert "detect_broken_pconn on" in content
        assert "tls_outgoing_options min-version=1.2" in content
        assert "dns_v4_first on" in content


def test_generate_config_dpi_prevention_disabled():
    """Test that DPI prevention directives are absent when disabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        gen = SquidConfigGenerator("no-dpi-proxy", 3128, False, dpi_prevention=False)
        gen.generate_config(config_file)

        content = config_file.read_text()

        # DPI prevention directives must NOT be present
        assert "httpd_suppress_version_string" not in content
        assert "visible_hostname localhost" not in content
        assert "follow_x_forwarded_for deny all" not in content
        assert "reply_header_access X-Cache deny all" not in content
        assert "tls_outgoing_options" not in content
        assert "dns_v4_first" not in content


def test_generate_config_dpi_prevention_default_is_disabled():
    """Test that DPI prevention is disabled by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        gen = SquidConfigGenerator("default-proxy", 3128, False)
        gen.generate_config(config_file)

        content = config_file.read_text()

        # Without explicitly enabling DPI, it should be absent
        assert "httpd_suppress_version_string" not in content
        assert "dns_v4_first" not in content


def test_generate_config_dpi_prevention_with_https():
    """Test DPI prevention combined with HTTPS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        gen = SquidConfigGenerator("dpi-https-proxy", 3128, https_enabled=True, dpi_prevention=True)
        gen.generate_config(config_file)

        content = config_file.read_text()

        # Both HTTPS and DPI prevention should be present
        assert "https_port 3128" in content
        assert "tls-cert=" in content
        assert "httpd_suppress_version_string on" in content
        assert "dns_v4_first on" in content
        assert "tls_outgoing_options min-version=1.2" in content


def test_dpi_prevention_init_stored():
    """Test that dpi_prevention is stored on the generator instance."""
    gen = SquidConfigGenerator("test", 3128, dpi_prevention=True)
    assert gen.dpi_prevention is True

    gen2 = SquidConfigGenerator("test", 3128, dpi_prevention=False)
    assert gen2.dpi_prevention is False

    gen3 = SquidConfigGenerator("test", 3128)
    assert gen3.dpi_prevention is False
