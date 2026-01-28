"""Tests for CertificateManager."""
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app"))

from cert_manager import CertificateManager


@pytest.mark.asyncio
async def test_cert_manager_init(temp_dir):
    """Test CertificateManager initialization."""
    certs_dir = temp_dir / "certs"
    cert_manager = CertificateManager(certs_dir, "test-instance")
    
    assert cert_manager.certs_dir == certs_dir
    assert cert_manager.instance_name == "test-instance"
    assert cert_manager.cert_dir == certs_dir / "test-instance"
    assert cert_manager.cert_file == cert_manager.cert_dir / "proxyCA.pem"
    assert cert_manager.key_file == cert_manager.cert_dir / "proxyCA.key"


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
    
    # Check permissions
    assert oct(key_file.stat().st_mode)[-3:] == "600"
    assert oct(cert_file.parent.stat().st_mode)[-3:] == "755"


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
    assert b"BEGIN PRIVATE KEY" in key_content
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
