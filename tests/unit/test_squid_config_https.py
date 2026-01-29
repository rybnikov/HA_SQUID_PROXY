"""Unit tests for HTTPS configuration in squid_config.py.

These tests verify that the squid.conf generated for HTTPS instances
does NOT contain ssl_bump directive, which would require a signing certificate.
"""
import tempfile
from pathlib import Path

import pytest


def test_https_config_no_ssl_bump():
    """Verify HTTPS config does NOT contain ssl_bump directive.
    
    ssl_bump requires a signing certificate for dynamic certificate generation.
    We only want clients to connect to the proxy via HTTPS (encrypted connection),
    not SSL bumping/interception. Therefore ssl_bump should NOT be present.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app"))
    from squid_config import SquidConfigGenerator
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        gen = SquidConfigGenerator("https-test", 3128, https_enabled=True)
        gen.generate_config(config_file)
        
        content = config_file.read_text()
        
        # CRITICAL: ssl_bump should NOT be in HTTPS config
        # ssl_bump requires a signing certificate which causes:
        # "FATAL: No valid signing certificate configured for HTTPS_port"
        assert "ssl_bump" not in content, (
            "ssl_bump directive found in config! This will cause Squid to fail with "
            "'No valid signing certificate configured for HTTPS_port'. "
            "ssl_bump should not be used for simple HTTPS proxy connections."
        )


def test_https_config_has_tls_cert_and_key():
    """Verify HTTPS config has tls-cert and tls-key without quotes."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app"))
    from squid_config import SquidConfigGenerator
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        gen = SquidConfigGenerator("https-test", 3128, https_enabled=True)
        gen.generate_config(config_file)
        
        content = config_file.read_text()
        
        # Should have https_port with tls-cert and tls-key
        assert "https_port 3128" in content
        assert "tls-cert=" in content
        assert "tls-key=" in content
        
        # Paths should NOT be quoted (quotes can cause issues)
        assert 'tls-cert="' not in content, "tls-cert path should not be quoted"
        assert 'tls-key="' not in content, "tls-key path should not be quoted"


def test_https_config_correct_certificate_paths():
    """Verify certificate paths are correct and absolute."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app"))
    from squid_config import SquidConfigGenerator
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        gen = SquidConfigGenerator("my-proxy", 3129, https_enabled=True)
        gen.generate_config(config_file)
        
        content = config_file.read_text()
        
        # Certificate paths should be absolute and instance-specific
        assert "tls-cert=/data/squid_proxy_manager/certs/my-proxy/squid.crt" in content
        assert "tls-key=/data/squid_proxy_manager/certs/my-proxy/squid.key" in content


def test_http_config_no_https_directives():
    """Verify HTTP-only config has no HTTPS-related directives."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app"))
    from squid_config import SquidConfigGenerator
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        gen = SquidConfigGenerator("http-test", 3128, https_enabled=False)
        gen.generate_config(config_file)
        
        content = config_file.read_text()
        
        # HTTP config should use http_port, not https_port
        assert "http_port 3128" in content
        assert "https_port" not in content
        assert "tls-cert" not in content
        assert "tls-key" not in content
        assert "ssl_bump" not in content


def test_https_config_format_for_squid_5_9():
    """Verify config format is compatible with Squid 5.9.
    
    Squid 5.9 https_port syntax:
    https_port [ip:]port tls-cert=path tls-key=path [options]
    
    NOT:
    https_port [ip:]port cert=path key=path  (old syntax)
    https_port [ip:]port ssl-bump ...  (requires signing cert)
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app"))
    from squid_config import SquidConfigGenerator
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "squid.conf"
        gen = SquidConfigGenerator("squid59-test", 3130, https_enabled=True)
        gen.generate_config(config_file)
        
        content = config_file.read_text()
        
        # Find the https_port line
        https_lines = [line for line in content.split('\n') if line.startswith('https_port')]
        assert len(https_lines) == 1, f"Expected exactly one https_port line, found {len(https_lines)}"
        
        https_line = https_lines[0]
        
        # Verify format: https_port PORT tls-cert=PATH tls-key=PATH
        assert https_line.startswith("https_port 3130 "), f"Unexpected https_port format: {https_line}"
        assert "tls-cert=" in https_line, f"Missing tls-cert in: {https_line}"
        assert "tls-key=" in https_line, f"Missing tls-key in: {https_line}"
        
        # Should NOT contain old-style options
        assert "cert=" not in https_line or "tls-cert=" in https_line
        assert "key=" not in https_line or "tls-key=" in https_line
