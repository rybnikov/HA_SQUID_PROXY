"""Integration tests for HTTPS certificate file access and validation."""
import asyncio
import subprocess
from pathlib import Path

import pytest

# Add app directory to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../squid_proxy_manager/rootfs/app"))


@pytest.mark.asyncio
async def test_certificate_file_permissions(proxy_manager, test_instance_name, test_port):
    """Test that certificate files have correct permissions for Squid access."""
    # Create HTTPS instance
    instance = await proxy_manager.create_instance(
        name=test_instance_name,
        port=test_port,
        https_enabled=True,
        users=[],
    )
    
    await asyncio.sleep(1)
    
    # Verify certificates exist
    from proxy_manager import CERTS_DIR
    cert_dir = CERTS_DIR / test_instance_name
    cert_file = cert_dir / "squid.crt"
    key_file = cert_dir / "squid.key"
    
    assert cert_file.exists()
    assert key_file.exists()
    
    # Verify permissions are 0o644 (readable by all, including Squid)
    cert_mode = oct(cert_file.stat().st_mode)[-3:]
    key_mode = oct(key_file.stat().st_mode)[-3:]
    
    assert cert_mode == "644", f"Certificate file should have 644 permissions, got {cert_mode}"
    assert key_mode == "644", f"Key file should have 644 permissions, got {key_mode}"


@pytest.mark.asyncio
async def test_certificate_openssl_validation(proxy_manager, test_instance_name, test_port):
    """Test that certificates can be validated using OpenSSL."""
    # Create HTTPS instance
    instance = await proxy_manager.create_instance(
        name=test_instance_name,
        port=test_port,
        https_enabled=True,
        users=[],
    )
    
    await asyncio.sleep(1)
    
    # Verify certificates can be validated with OpenSSL
    from proxy_manager import CERTS_DIR
    cert_file = CERTS_DIR / test_instance_name / "squid.crt"
    
    # Test OpenSSL can read and parse the certificate
    result = subprocess.run(
        ["openssl", "x509", "-in", str(cert_file), "-noout", "-text"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    
    assert result.returncode == 0, f"OpenSSL validation failed: {result.stderr}"
    assert "Certificate:" in result.stdout or "Subject:" in result.stdout


@pytest.mark.asyncio
async def test_certificate_file_readability(proxy_manager, test_instance_name, test_port):
    """Test that certificate files are readable."""
    # Create HTTPS instance
    instance = await proxy_manager.create_instance(
        name=test_instance_name,
        port=test_port,
        https_enabled=True,
        users=[],
    )
    
    await asyncio.sleep(1)
    
    # Verify files are readable
    from proxy_manager import CERTS_DIR
    cert_file = CERTS_DIR / test_instance_name / "squid.crt"
    key_file = CERTS_DIR / test_instance_name / "squid.key"
    
    # Test files can be opened and read
    with open(cert_file, "r") as f:
        cert_content = f.read()
        assert "BEGIN CERTIFICATE" in cert_content
        assert "END CERTIFICATE" in cert_content
    
    with open(key_file, "r") as f:
        key_content = f.read()
        assert "BEGIN" in key_content
        assert "END" in key_content


@pytest.mark.asyncio
async def test_squid_config_certificate_paths(proxy_manager, test_instance_name, test_port):
    """Test that Squid config has correct certificate paths."""
    # Create HTTPS instance
    instance = await proxy_manager.create_instance(
        name=test_instance_name,
        port=test_port,
        https_enabled=True,
        users=[],
    )
    
    await asyncio.sleep(1)
    
    # Verify squid.conf has correct paths
    from proxy_manager import CONFIG_DIR
    config_file = CONFIG_DIR / test_instance_name / "squid.conf"
    
    assert config_file.exists()
    config_content = config_file.read_text()
    
    # Check for https_port directive with tls-cert and tls-key (no quotes around paths)
    assert "https_port" in config_content
    assert "tls-cert=" in config_content
    assert "tls-key=" in config_content
    
    # Verify paths are absolute (no quotes in the new format)
    import re
    # Match tls-cert=/path/to/cert (no quotes)
    cert_path_match = re.search(r'tls-cert=(/[^\s]+)', config_content)
    key_path_match = re.search(r'tls-key=(/[^\s]+)', config_content)
    
    assert cert_path_match, f"Certificate path not found in config: {config_content}"
    assert key_path_match, f"Key path not found in config: {config_content}"
    
    cert_path = cert_path_match.group(1)
    key_path = key_path_match.group(1)
    
    assert cert_path.startswith("/"), f"Certificate path should be absolute: {cert_path}"
    assert key_path.startswith("/"), f"Key path should be absolute: {key_path}"
    
    # Verify paths point to actual files
    # Note: Paths in config are absolute container paths, but in tests we use relative paths
    # So we need to check if the files exist relative to the test environment
    from proxy_manager import CERTS_DIR
    expected_cert = CERTS_DIR / test_instance_name / "squid.crt"
    expected_key = CERTS_DIR / test_instance_name / "squid.key"
    
    assert expected_cert.exists(), f"Certificate file does not exist: {expected_cert}"
    assert expected_key.exists(), f"Key file does not exist: {expected_key}"
    
    # Also verify the paths in config match the expected structure
    assert test_instance_name in cert_path, f"Certificate path should contain instance name: {cert_path}"
    assert test_instance_name in key_path, f"Key path should contain instance name: {key_path}"
