"""Tests for SquidConfigGenerator."""
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app"))

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
        gen = SquidConfigGenerator("test-instance", 3128, False)
        gen.generate_config(config_file)
        
        assert config_file.exists()
        content = config_file.read_text()
        
        # Check basic settings
        assert "http_port 3128" in content
        assert "test-instance" in content
        assert "auth_param basic" in content
        assert "/data/squid_proxy_manager/test-instance/passwd" in content
        
        # Check permissions
        assert oct(config_file.stat().st_mode)[-3:] == "644"


def test_generate_config_https():
    """Test generating Squid configuration with HTTPS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        gen = SquidConfigGenerator("test-instance", 8080, True)
        gen.generate_config(config_file)
        
        assert config_file.exists()
        content = config_file.read_text()
        
        # Check HTTPS settings - no ssl_bump (causes signing cert requirement), no quotes on paths
        assert "https_port 8080" in content
        assert "ssl_bump" not in content  # ssl_bump was removed to fix HTTPS
        assert "tls-cert=/data/squid_proxy_manager/certs/test-instance/squid.crt" in content
        assert "tls-key=/data/squid_proxy_manager/certs/test-instance/squid.key" in content


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
