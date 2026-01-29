"""Utilities for detecting network capabilities in test environment."""
import socket
import pytest


def can_bind_port(port: int = None) -> bool:
    """Check if we can bind to a port (network capability available).
    
    Args:
        port: Port number to test (None or 0 to let OS assign)
        
    Returns:
        True if port binding is available, False otherwise
    """
    if port is None:
        port = 0  # Let OS assign port
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))
            return True
    except (OSError, PermissionError):
        return False


def skip_if_no_network():
    """Pytest skip decorator for tests requiring network port binding.
    
    Usage:
        @skip_if_no_network()
        async def test_that_needs_network():
            ...
    """
    if not can_bind_port():
        pytest.skip("Network port binding not available (sandbox environment)")


def check_port_connectivity(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a port is listening and accepting connections.
    
    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Connection timeout in seconds
        
    Returns:
        True if port is accessible, False otherwise
    """
    if not can_bind_port():
        # If we can't bind ports, we can't test connectivity
        return False
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception:
        return False
