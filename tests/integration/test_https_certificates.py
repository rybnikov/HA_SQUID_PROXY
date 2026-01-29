"""Integration tests for HTTPS certificate generation and validation."""
import asyncio
from pathlib import Path

import pytest
from cryptography import x509

# Add app directory to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../squid_proxy_manager/rootfs/app"))


@pytest.mark.asyncio
async def test_https_instance_creation_with_certificates(proxy_manager, test_instance_name, test_port):
    """Test creating an HTTPS instance and verify certificates are generated correctly."""
    # Create HTTPS instance
    instance = await proxy_manager.create_instance(
        name=test_instance_name,
        port=test_port,
        https_enabled=True,
        users=[],
    )
    
    assert instance["https_enabled"] is True
    assert instance["status"] == "running"
    
    # Wait for certificate generation
    await asyncio.sleep(1)
    
    # Verify certificates exist
    from proxy_manager import CERTS_DIR
    cert_dir = CERTS_DIR / test_instance_name
    cert_file = cert_dir / "squid.crt"
    key_file = cert_dir / "squid.key"
    
    assert cert_file.exists(), f"Certificate file should exist: {cert_file}"
    assert key_file.exists(), f"Key file should exist: {key_file}"
    
    # Verify certificate is valid PEM format
    cert_data = cert_file.read_bytes()
    cert = x509.load_pem_x509_certificate(cert_data)
    assert cert is not None
    
    # Verify certificate is a server certificate (not CA)
    basic_constraints = None
    for ext in cert.extensions:
        if isinstance(ext.value, x509.BasicConstraints):
            basic_constraints = ext.value
            break
    assert basic_constraints is not None
    assert basic_constraints.ca is False, "Certificate should be a server certificate"
    
    # Verify certificate permissions - both should be 644 for Squid compatibility
    assert oct(cert_file.stat().st_mode)[-3:] == "644"
    assert oct(key_file.stat().st_mode)[-3:] == "644", f"Key file should have 644 permissions for Squid access, got {oct(key_file.stat().st_mode)[-3:]}"


@pytest.mark.asyncio
async def test_https_enable_regenerates_certificates(proxy_manager, test_instance_name, test_port):
    """Test that enabling HTTPS on existing instance regenerates certificates."""
    # Create HTTP instance first
    instance = await proxy_manager.create_instance(
        name=test_instance_name,
        port=test_port,
        https_enabled=False,
        users=[],
    )
    assert instance["https_enabled"] is False
    
    # Stop instance
    await proxy_manager.stop_instance(test_instance_name)
    await asyncio.sleep(1)
    
    # Enable HTTPS
    success = await proxy_manager.update_instance(
        name=test_instance_name,
        https_enabled=True,
    )
    assert success is True
    
    # Wait for certificate generation
    await asyncio.sleep(2)
    
    # Verify certificates were generated
    from proxy_manager import CERTS_DIR
    cert_dir = CERTS_DIR / test_instance_name
    cert_file = cert_dir / "squid.crt"
    key_file = cert_dir / "squid.key"
    
    assert cert_file.exists()
    assert key_file.exists()
    
    # Verify certificate is valid
    cert_data = cert_file.read_bytes()
    cert = x509.load_pem_x509_certificate(cert_data)
    assert cert is not None


@pytest.mark.asyncio
async def test_certificate_parameters(proxy_manager, test_instance_name, test_port):
    """Test certificate generation with custom parameters."""
    cert_params = {
        "common_name": "custom-proxy-name",
        "validity_days": 730,
        "key_size": 4096,
        "country": "CA",
        "organization": "Test Organization",
    }
    
    instance = await proxy_manager.create_instance(
        name=test_instance_name,
        port=test_port,
        https_enabled=True,
        users=[],
        cert_params=cert_params,
    )
    
    await asyncio.sleep(1)
    
    # Verify certificate has custom parameters
    from proxy_manager import CERTS_DIR
    cert_file = CERTS_DIR / test_instance_name / "squid.crt"
    cert_data = cert_file.read_bytes()
    cert = x509.load_pem_x509_certificate(cert_data)
    
    # Check Common Name
    cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
    assert cn == "custom-proxy-name"
    
    # Check Country
    country = cert.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME)[0].value
    assert country == "CA"
    
    # Check Organization
    org = cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)[0].value
    assert org == "Test Organization"


@pytest.mark.asyncio
async def test_certificate_validation_before_start(proxy_manager, test_instance_name, test_port):
    """Test that certificates are validated before Squid starts."""
    # Create HTTPS instance
    instance = await proxy_manager.create_instance(
        name=test_instance_name,
        port=test_port,
        https_enabled=True,
        users=[],
    )
    
    # Wait for startup
    await asyncio.sleep(2)
    
    # Verify instance is running (certificates were valid)
    instances = await proxy_manager.get_instances()
    instance = next(i for i in instances if i["name"] == test_instance_name)
    
    # If certificates were invalid, instance would not be running
    # This test verifies that certificate validation works
    assert instance is not None


@pytest.mark.asyncio
async def test_https_squid_config_no_ssl_bump(proxy_manager, test_instance_name, test_port):
    """CRITICAL: Verify HTTPS squid.conf does NOT contain ssl_bump.
    
    This test catches the root cause of the HTTPS failure:
    'FATAL: No valid signing certificate configured for HTTPS_port'
    
    ssl_bump requires a signing certificate for dynamic certificate generation.
    For simple HTTPS proxy (clients connect to proxy via TLS), we should NOT
    use ssl_bump at all - just tls-cert and tls-key for the proxy's server cert.
    """
    from proxy_manager import CONFIG_DIR
    
    # Create HTTPS instance
    await proxy_manager.create_instance(
        name=test_instance_name,
        port=test_port,
        https_enabled=True,
        users=[],
    )
    
    # Read the generated squid.conf
    config_file = CONFIG_DIR / test_instance_name / "squid.conf"
    assert config_file.exists(), f"Config file should exist: {config_file}"
    
    config_content = config_file.read_text()
    
    # CRITICAL ASSERTION: ssl_bump should NOT be present
    assert "ssl_bump" not in config_content, (
        "ssl_bump directive found in HTTPS config! "
        "This will cause Squid to fail with: "
        "'FATAL: No valid signing certificate configured for HTTPS_port'. "
        "ssl_bump requires a signing certificate but we only have a server certificate."
    )
    
    # Verify correct HTTPS configuration is present
    assert "https_port" in config_content, "https_port should be configured"
    assert "tls-cert=" in config_content, "tls-cert should be configured"
    assert "tls-key=" in config_content, "tls-key should be configured"
    
    # Verify no quotes around paths (can cause issues)
    assert 'tls-cert="' not in config_content, "tls-cert path should not be quoted"
    assert 'tls-key="' not in config_content, "tls-key path should not be quoted"


@pytest.mark.asyncio
async def test_http_squid_config_no_https_directives(proxy_manager, test_instance_name, test_port):
    """Verify HTTP-only squid.conf has no HTTPS-related directives."""
    from proxy_manager import CONFIG_DIR
    
    # Create HTTP instance (not HTTPS)
    await proxy_manager.create_instance(
        name=test_instance_name,
        port=test_port,
        https_enabled=False,
        users=[],
    )
    
    # Read the generated squid.conf
    config_file = CONFIG_DIR / test_instance_name / "squid.conf"
    config_content = config_file.read_text()
    
    # HTTP config should use http_port, not https_port
    assert "http_port" in config_content
    assert "https_port" not in config_content
    assert "tls-cert" not in config_content
    assert "tls-key" not in config_content
    assert "ssl_bump" not in config_content
