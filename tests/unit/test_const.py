"""Unit tests for constants."""
from custom_components.squid_proxy_manager.const import DOMAIN, DEFAULT_PORT


def test_domain():
    """Test that DOMAIN is set correctly."""
    assert DOMAIN == "squid_proxy_manager"


def test_default_port():
    """Test that default port is valid."""
    assert DEFAULT_PORT >= 1024
    assert DEFAULT_PORT <= 65535
