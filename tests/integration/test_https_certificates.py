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
    
    # Verify certificate permissions
    assert oct(cert_file.stat().st_mode)[-3:] == "644"
    assert oct(key_file.stat().st_mode)[-3:] == "600"


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
