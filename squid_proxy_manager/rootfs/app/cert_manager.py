"""HTTPS certificate generation and management."""
from __future__ import annotations

import ipaddress
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

_LOGGER = logging.getLogger(__name__)

CERT_KEY_SIZE = 2048
CERT_VALIDITY_DAYS = 365
PERM_PRIVATE_KEY = 0o644  # Changed to 0o644 for Squid compatibility (Squid runs as different user)
PERM_CERTIFICATE = 0o644
PERM_DIRECTORY = 0o755


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
        self.cert_file = self.cert_dir / "squid.crt"
        self.key_file = self.cert_dir / "squid.key"

    async def generate_certificate(
        self,
        validity_days: int = CERT_VALIDITY_DAYS,
        key_size: int = CERT_KEY_SIZE,
        common_name: str | None = None,
        country: str = "US",
        organization: str = "Squid Proxy Manager",
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
            self.cert_dir.mkdir(parents=True, exist_ok=True)
            self.cert_dir.chmod(PERM_DIRECTORY)

            # Generate private key
            _LOGGER.info("Generating %d-bit RSA key for %s", key_size, self.instance_name)
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
            )

            # Create certificate
            cn = common_name or f"squid-proxy-{self.instance_name}"
            subject = issuer = x509.Name(
                [
                    x509.NameAttribute(NameOID.COUNTRY_NAME, country),
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Home Assistant"),
                    x509.NameAttribute(NameOID.LOCALITY_NAME, "Proxy"),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                    x509.NameAttribute(NameOID.COMMON_NAME, cn),
                ]
            )

            # Build server certificate (not CA certificate)
            # Squid needs a server certificate for https_port, not a CA certificate
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.now(timezone.utc))
                .not_valid_after(datetime.now(timezone.utc) + timedelta(days=validity_days))
                .add_extension(
                    x509.BasicConstraints(ca=False, path_length=None),
                    critical=True,
                )
                .add_extension(
                    x509.KeyUsage(
                        digital_signature=True,
                        content_commitment=False,
                        key_encipherment=True,
                        data_encipherment=False,
                        key_agreement=False,
                        key_cert_sign=False,  # Not a CA certificate
                        crl_sign=False,  # Not a CA certificate
                        encipher_only=False,
                        decipher_only=False,
                    ),
                    critical=True,
                )
                .add_extension(
                    x509.ExtendedKeyUsage(
                        [
                            x509.ExtendedKeyUsageOID.SERVER_AUTH,
                        ]
                    ),
                    critical=False,
                )
                .add_extension(
                    x509.SubjectAlternativeName(
                        [
                            x509.DNSName("localhost"),
                            x509.DNSName("*.local"),
                            x509.DNSName(f"squid-proxy-{self.instance_name}"),
                            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                        ]
                    ),
                    critical=False,
                )
                .sign(private_key, hashes.SHA256())
            )

            # Write certificate
            cert_pem = cert.public_bytes(serialization.Encoding.PEM)
            self.cert_file.write_bytes(cert_pem)
            self.cert_file.chmod(PERM_CERTIFICATE)
            # Ensure certificate is readable by Squid (which may run as different user)
            # Use 0o644 (readable by all) instead of 0o600 for key to allow Squid access
            # In production, Squid typically runs as 'nobody' or 'squid' user
            # So we need world-readable permissions or proper ownership

            # Write private key - use 0o644 for Squid compatibility
            # Squid needs to read the key, and it may run as a different user
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            self.key_file.write_bytes(key_pem)
            # Use 0o644 instead of 0o600 so Squid (running as different user) can read it
            # This is acceptable in containerized environments where access is controlled
            self.key_file.chmod(PERM_CERTIFICATE)  # 0o644 - readable by all

            # Verify certificate can be loaded (validate PEM format)
            try:
                loaded_cert = x509.load_pem_x509_certificate(cert_pem)
                _LOGGER.info(
                    "Generated and verified server certificate for %s: %s (CN: %s, valid for %d days)",
                    self.instance_name,
                    self.cert_file,
                    cn,
                    validity_days,
                )
            except Exception as ex:
                _LOGGER.error("Failed to verify generated certificate: %s", ex)
                raise RuntimeError(f"Generated certificate is invalid: {ex}")

            return (self.cert_file, self.key_file)

        except Exception as ex:
            _LOGGER.error("Failed to generate certificate for %s: %s", self.instance_name, ex)
            raise
