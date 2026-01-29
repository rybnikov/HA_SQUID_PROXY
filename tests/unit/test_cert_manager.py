"""Tests for CertificateManager."""

# Add parent directory to path for imports
import sys
from pathlib import Path

import pytest
from cryptography import x509

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app")
)

from cert_manager import CertificateManager


@pytest.mark.asyncio
async def test_cert_manager_init(temp_dir):
    """Test CertificateManager initialization."""
    certs_dir = temp_dir / "certs"
    cert_manager = CertificateManager(certs_dir, "test-instance")

    assert cert_manager.certs_dir == certs_dir
    assert cert_manager.instance_name == "test-instance"
    assert cert_manager.cert_dir == certs_dir / "test-instance"
    assert cert_manager.cert_file == cert_manager.cert_dir / "squid.crt"
    assert cert_manager.key_file == cert_manager.cert_dir / "squid.key"


@pytest.mark.asyncio
async def test_generate_certificate(temp_dir):
    """Test certificate generation."""
    certs_dir = temp_dir / "certs"
    cert_manager = CertificateManager(certs_dir, "test-instance")

    cert_file, key_file = await cert_manager.generate_certificate()

    assert cert_file.exists()
    assert key_file.exists()
    assert cert_file == cert_manager.cert_file
    assert key_file == cert_manager.key_file

    # Check permissions - key file is 0o640 for restricted access
    assert (
        oct(key_file.stat().st_mode)[-3:] == "640"
    ), f"Key file permissions should be 640, got {oct(key_file.stat().st_mode)[-3:]}"
    assert oct(cert_file.stat().st_mode)[-3:] == "640"  # Certificate file permissions
    assert oct(cert_file.parent.stat().st_mode)[-3:] == "750"

    # Verify certificate is a server certificate (not CA)
    cert_data = cert_file.read_bytes()
    cert = x509.load_pem_x509_certificate(cert_data)

    # Check BasicConstraints - should be ca=False for server certificate
    basic_constraints = None
    for ext in cert.extensions:
        if isinstance(ext.value, x509.BasicConstraints):
            basic_constraints = ext.value
            break
    assert basic_constraints is not None, "BasicConstraints extension should be present"
    assert (
        basic_constraints.ca is False
    ), "Certificate should be a server certificate (ca=False), not CA"

    # Check KeyUsage - should NOT have key_cert_sign (that's for CA certs)
    key_usage = None
    for ext in cert.extensions:
        if isinstance(ext.value, x509.KeyUsage):
            key_usage = ext.value
            break
    assert key_usage is not None, "KeyUsage extension should be present"
    assert key_usage.key_cert_sign is False, "Server certificate should not have key_cert_sign=True"
    assert (
        key_usage.digital_signature is True
    ), "Server certificate should have digital_signature=True"
    assert (
        key_usage.key_encipherment is True
    ), "Server certificate should have key_encipherment=True"


@pytest.mark.asyncio
async def test_generate_certificate_custom_validity(temp_dir):
    """Test certificate generation with custom validity."""
    certs_dir = temp_dir / "certs"
    cert_manager = CertificateManager(certs_dir, "test-instance")

    cert_file, key_file = await cert_manager.generate_certificate(validity_days=730)

    assert cert_file.exists()
    assert key_file.exists()

    # Verify certificate content
    cert_content = cert_file.read_bytes()
    assert b"BEGIN CERTIFICATE" in cert_content
    assert b"END CERTIFICATE" in cert_content


@pytest.mark.asyncio
async def test_generate_certificate_custom_key_size(temp_dir):
    """Test certificate generation with custom key size."""
    certs_dir = temp_dir / "certs"
    cert_manager = CertificateManager(certs_dir, "test-instance")

    cert_file, key_file = await cert_manager.generate_certificate(key_size=4096)

    assert cert_file.exists()
    assert key_file.exists()

    # Verify key content
    key_content = key_file.read_bytes()
    assert b"BEGIN PRIVATE KEY" in key_content  # pragma: allowlist secret
    assert b"END PRIVATE KEY" in key_content


@pytest.mark.asyncio
async def test_generate_certificate_multiple_instances(temp_dir):
    """Test generating certificates for multiple instances."""
    certs_dir = temp_dir / "certs"

    for instance_name in ["instance1", "instance2", "instance3"]:
        cert_manager = CertificateManager(certs_dir, instance_name)
        cert_file, key_file = await cert_manager.generate_certificate()

        assert cert_file.exists()
        assert key_file.exists()
        assert instance_name in str(cert_file.parent)

        # Verify each certificate is a valid server certificate
        cert_data = cert_file.read_bytes()
        cert = x509.load_pem_x509_certificate(cert_data)
        assert cert is not None


@pytest.mark.asyncio
async def test_generate_certificate_with_parameters(temp_dir):
    """Test certificate generation with custom parameters."""
    certs_dir = temp_dir / "certs"
    cert_manager = CertificateManager(certs_dir, "test-instance")

    cert_file, key_file = await cert_manager.generate_certificate(
        validity_days=730,
        key_size=4096,
        common_name="custom-cn",
        country="CA",
        organization="Test Org",
    )

    assert cert_file.exists()
    assert key_file.exists()

    # Verify certificate content
    cert_data = cert_file.read_bytes()
    cert = x509.load_pem_x509_certificate(cert_data)

    # Check Common Name
    cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
    assert cn == "custom-cn"

    # Check Country
    country = cert.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME)[0].value
    assert country == "CA"

    # Check Organization
    org = cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)[0].value
    assert org == "Test Org"
