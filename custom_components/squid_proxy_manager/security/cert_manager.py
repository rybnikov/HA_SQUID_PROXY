"""HTTPS certificate generation and management."""
from __future__ import annotations

import ipaddress
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from ..const import CERT_KEY_SIZE, CERT_VALIDITY_DAYS, PERM_PRIVATE_KEY, PERM_DIRECTORY
from .security_utils import ensure_secure_directory, set_file_permissions, secure_file_write

_LOGGER = logging.getLogger(__name__)


class CertificateManager:
    """Manages HTTPS certificates for proxy instances."""

    def __init__(self, certs_dir: Path, instance_name: str) -> None:
        """Initialize certificate manager.

        Args:
            certs_dir: Directory to store certificates
            instance_name: Name of the proxy instance
        """
        self.certs_dir = certs_dir
        self.instance_name = instance_name
        self.cert_dir = certs_dir / instance_name
        self.cert_file = self.cert_dir / "proxyCA.pem"
        self.key_file = self.cert_dir / "proxyCA.key"

    async def generate_certificate(
        self,
        validity_days: int = CERT_VALIDITY_DAYS,
        key_size: int = CERT_KEY_SIZE,
    ) -> tuple[Path, Path]:
        """Generate a self-signed certificate and private key.

        Args:
            validity_days: Certificate validity in days
            key_size: RSA key size in bits

        Returns:
            Tuple of (certificate_path, key_path)

        Raises:
            Exception: If certificate generation fails
        """
        try:
            # Ensure certificate directory exists
            ensure_secure_directory(self.cert_dir)

            # Generate private key
            _LOGGER.info("Generating %d-bit RSA key for %s", key_size, self.instance_name)
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
            )

            # Create certificate
            subject = issuer = x509.Name(
                [
                    x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Home Assistant"),
                    x509.NameAttribute(NameOID.LOCALITY_NAME, "Proxy"),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Squid Proxy Manager"),
                    x509.NameAttribute(NameOID.COMMON_NAME, f"squid-proxy-{self.instance_name}"),
                ]
            )

            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.utcnow())
                .not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
                .add_extension(
                    x509.SubjectAlternativeName(
                        [
                            x509.DNSName("localhost"),
                            x509.DNSName("*.local"),
                            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                        ]
                    ),
                    critical=False,
                )
                .sign(private_key, hashes.SHA256())
            )

            # Write certificate
            cert_pem = cert.public_bytes(serialization.Encoding.PEM)
            secure_file_write(self.cert_file, cert_pem, PERM_DIRECTORY)

            # Write private key with restricted permissions
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            secure_file_write(self.key_file, key_pem, PERM_PRIVATE_KEY)

            _LOGGER.info(
                "Generated certificate for %s: %s (valid for %d days)",
                self.instance_name,
                self.cert_file,
                validity_days,
            )

            return (self.cert_file, self.key_file)

        except Exception as ex:
            _LOGGER.error("Failed to generate certificate for %s: %s", self.instance_name, ex)
            raise

    def get_certificate_paths(self) -> tuple[Path | None, Path | None]:
        """Get paths to certificate and key files.

        Returns:
            Tuple of (certificate_path, key_path) or (None, None) if not found
        """
        cert_exists = self.cert_file.exists()
        key_exists = self.key_file.exists()

        if cert_exists and key_exists:
            return (self.cert_file, self.key_file)
        return (None, None)

    def get_certificate_expiry(self) -> datetime | None:
        """Get certificate expiry date.

        Returns:
            Expiry datetime or None if certificate not found
        """
        if not self.cert_file.exists():
            return None

        try:
            cert_data = self.cert_file.read_bytes()
            cert = x509.load_pem_x509_certificate(cert_data)
            return cert.not_valid_after
        except Exception as ex:
            _LOGGER.error("Failed to read certificate expiry: %s", ex)
            return None

    def is_certificate_valid(self) -> bool:
        """Check if certificate is valid (exists and not expired).

        Returns:
            True if certificate is valid, False otherwise
        """
        expiry = self.get_certificate_expiry()
        if expiry is None:
            return False
        return datetime.utcnow() < expiry

    def use_existing_certificate(self, cert_path: Path, key_path: Path) -> tuple[Path, Path]:
        """Use existing certificate files.

        Args:
            cert_path: Path to existing certificate file
            key_path: Path to existing private key file

        Returns:
            Tuple of (certificate_path, key_path) in the instance directory

        Raises:
            ValueError: If certificate or key files are invalid
        """
        if not cert_path.exists():
            raise ValueError(f"Certificate file not found: {cert_path}")
        if not key_path.exists():
            raise ValueError(f"Private key file not found: {key_path}")

        # Validate certificate
        try:
            cert_data = cert_path.read_bytes()
            cert = x509.load_pem_x509_certificate(cert_data)
            if datetime.utcnow() >= cert.not_valid_after:
                raise ValueError("Certificate has expired")
        except Exception as ex:
            raise ValueError(f"Invalid certificate: {ex}") from ex

        # Validate private key
        try:
            key_data = key_path.read_bytes()
            serialization.load_pem_private_key(key_data, password=None)
        except Exception as ex:
            raise ValueError(f"Invalid private key: {ex}") from ex

        # Ensure certificate directory exists
        ensure_secure_directory(self.cert_dir)

        # Copy files to instance directory with secure permissions
        cert_content = cert_path.read_bytes()
        key_content = key_path.read_bytes()

        secure_file_write(self.cert_file, cert_content, PERM_DIRECTORY)
        secure_file_write(self.key_file, key_content, PERM_PRIVATE_KEY)

        _LOGGER.info("Using existing certificate for %s", self.instance_name)

        return (self.cert_file, self.key_file)
