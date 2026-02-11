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
