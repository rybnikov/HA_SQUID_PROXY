#!/usr/bin/env python3
"""Proxy instance management for the add-on using OS processes."""

from __future__ import annotations

import asyncio
import grp
import logging
import os
import pwd
import re
import signal
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("/data")
CONFIG_DIR = DATA_DIR / "squid_proxy_manager"
CERTS_DIR = CONFIG_DIR / "certs"
LOGS_DIR = CONFIG_DIR / "logs"
SQUID_BINARY = "/usr/sbin/squid"
NGINX_BINARY = "/usr/sbin/nginx"
INSTANCE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
VALID_PROXY_TYPES = ("squid", "tls_tunnel")


def _resolve_effective_user_group() -> tuple[int, int] | None:
    """Resolve a non-root user/group for Squid when running as root."""
    if os.getuid() != 0:
        return None
    for username in ("proxy", "squid", "nobody"):
        try:
            user = pwd.getpwnam(username)
            group = grp.getgrgid(user.pw_gid)
            return user.pw_uid, group.gr_gid
        except KeyError:
            continue
    return None


def _maybe_chown(path: Path, uid: int, gid: int) -> None:
    """Best-effort chown; ignore failures."""
    try:
        os.chown(path, uid, gid)
    except Exception:
        _LOGGER.debug("Failed to chown %s to %d:%d", path, uid, gid)


def validate_instance_name(name: str) -> str:
    """Validate and sanitize instance name to prevent path traversal/injection.

    Returns the sanitized name (basename-stripped) so CodeQL recognises the
    taint break.  Raises ValueError for invalid names.
    """
    # Strip any path component so a value like "../../etc" becomes "etc"
    safe = os.path.basename(name)
    if safe != name or not INSTANCE_NAME_RE.match(safe):
        raise ValueError("Instance name must be 1-64 chars and contain only a-z, 0-9, _ or -")
    return safe


def _safe_path(base: Path, name: str, *parts: str) -> Path:
    """Build a path under *base* from a validated instance name.

    Raises ValueError if the resolved path escapes *base*.
    """
    name = os.path.basename(name)  # CodeQL path-injection sanitiser
    if not INSTANCE_NAME_RE.match(name):
        raise ValueError("Instance name must be 1-64 chars and contain only a-z, 0-9, _ or -")
    result = (base / name / Path(*parts)) if parts else (base / name)
    resolved = result.resolve()
    base_resolved = base.resolve()
    if not str(resolved).startswith(str(base_resolved) + os.sep) and resolved != base_resolved:
        raise ValueError(f"Path escapes base directory: {result}")
    return result


def validate_port(port: int) -> None:
    """Validate port range."""
    if not 1024 <= port <= 65535:
        raise ValueError(f"Port out of range: {port}")


class ProxyInstanceManager:
    """Manages Squid proxy instances as OS processes."""

    def __init__(self):
        """Initialize the manager."""
        self.processes: dict[str, subprocess.Popen] = {}
        self._log_handles: dict[str, Any] = {}
        # Ensure directories exist
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CERTS_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_DIR.chmod(0o750)
        CERTS_DIR.chmod(0o750)
        LOGS_DIR.chmod(0o700)
        resolved = _resolve_effective_user_group()
        if resolved:
            uid, gid = resolved
            for d in [CONFIG_DIR, CERTS_DIR, LOGS_DIR]:
                _maybe_chown(d, uid, gid)
        _LOGGER.info("ProxyInstanceManager initialized using process-based architecture")

    async def create_instance(
        self,
        name: str,
        port: int,
        https_enabled: bool = False,
        users: list[dict[str, str]] | None = None,
        cert_params: dict[str, Any] | None = None,
        dpi_prevention: bool = False,
        proxy_type: str = "squid",
        forward_address: str | None = None,
        cover_domain: str | None = None,
    ) -> dict[str, Any]:
        """Create and start a new proxy instance.

        Args:
            name: Instance name
            port: Port number
            https_enabled: Whether HTTPS is enabled (squid only)
            users: List of users with username/password (squid only)
            dpi_prevention: Whether DPI prevention is enabled (squid only)
            proxy_type: 'squid' or 'tls_tunnel'
            forward_address: VPN server address (tls_tunnel only, e.g. 'vpn.example.com:1194')
            cover_domain: Domain for cover site SSL cert (tls_tunnel only)

        Returns:
            Dictionary with instance information
        """
        try:
            name = validate_instance_name(name)
            name = os.path.basename(name)  # CodeQL path-injection sanitiser
            validate_port(port)
            if proxy_type not in VALID_PROXY_TYPES:
                raise ValueError(
                    f"Invalid proxy_type: {proxy_type}. Must be one of {VALID_PROXY_TYPES}"
                )

            if proxy_type == "tls_tunnel":
                if not forward_address:
                    raise ValueError("forward_address is required for tls_tunnel proxy type")
                from tls_tunnel_config import validate_forward_address

                validate_forward_address(forward_address)

            # If instance already exists, stop it first to ensure clean start with new config/users
            if name in self.processes:
                _LOGGER.info("Instance %s already exists, stopping for recreation", name)
                await self.stop_instance(name)

            # Create directories
            instance_dir = _safe_path(CONFIG_DIR, name)

            # Clean up any leftover directories from Docker volume mounts
            for problematic_path in [
                instance_dir / "squid.conf",
                instance_dir / "passwd",
                _safe_path(CERTS_DIR, name, "squid.crt"),
                _safe_path(CERTS_DIR, name, "squid.key"),
            ]:
                if problematic_path.exists() and problematic_path.is_dir():
                    _LOGGER.info("Cleaning up problematic directory: %s", problematic_path)
                    import shutil

                    shutil.rmtree(problematic_path)

            instance_dir.mkdir(parents=True, exist_ok=True)
            instance_dir.chmod(0o750)
            instance_logs_dir = _safe_path(LOGS_DIR, name)
            instance_logs_dir.mkdir(parents=True, exist_ok=True)
            instance_logs_dir.chmod(0o700)
            resolved = _resolve_effective_user_group()
            if resolved:
                uid, gid = resolved
                _maybe_chown(instance_dir, uid, gid)
                _maybe_chown(instance_logs_dir, uid, gid)

            import json

            if proxy_type == "tls_tunnel":
                return await self._create_tls_tunnel_instance(
                    name, port, forward_address or "", cover_domain, instance_dir, instance_logs_dir
                )

            # --- Squid proxy type (existing behavior) ---

            # Generate Squid configuration
            from squid_config import SquidConfigGenerator

            config_gen = SquidConfigGenerator(
                name, port, https_enabled, str(CONFIG_DIR), dpi_prevention=dpi_prevention
            )
            config_file = instance_dir / "squid.conf"
            config_gen.generate_config(config_file)
            resolved = _resolve_effective_user_group()
            if resolved:
                uid, gid = resolved
                _maybe_chown(config_file, uid, gid)

            # Save instance metadata
            metadata_file = instance_dir / "instance.json"
            metadata = {
                "name": name,
                "proxy_type": "squid",
                "port": port,
                "https_enabled": https_enabled,
                "dpi_prevention": dpi_prevention,
                "created_at": __import__("datetime").datetime.now().isoformat(),
            }
            metadata_file.write_text(json.dumps(metadata, indent=2))

            # Handle HTTPS certificate - always regenerate when HTTPS is enabled
            cert_file = None
            key_file = None
            if https_enabled:
                _LOGGER.info("=== HTTPS Certificate Generation for %s ===", name)

                instance_cert_dir = _safe_path(CERTS_DIR, name)
                if instance_cert_dir.exists():
                    import shutil

                    shutil.rmtree(instance_cert_dir, ignore_errors=True)

                instance_cert_dir.mkdir(parents=True, exist_ok=True)
                instance_cert_dir.chmod(0o750)
                resolved = _resolve_effective_user_group()
                if resolved:
                    uid, gid = resolved
                    _maybe_chown(instance_cert_dir, uid, gid)

                from cert_manager import CertificateManager

                cert_manager = CertificateManager(CERTS_DIR, name)
                cert_params = cert_params or {}

                cert_file, key_file = await cert_manager.generate_certificate(
                    validity_days=cert_params.get("validity_days", 365),
                    key_size=cert_params.get("key_size", 2048),
                    common_name=cert_params.get("common_name"),
                    country=cert_params.get("country", "US"),
                    organization=cert_params.get("organization", "Squid Proxy Manager"),
                )

                await asyncio.sleep(0.5)

                if not cert_file.exists() or not key_file.exists():
                    raise RuntimeError(f"Failed to generate certificates for {name}")

                cert_stat = cert_file.stat()
                key_stat = key_file.stat()
                if cert_stat.st_size == 0 or key_stat.st_size == 0:
                    raise RuntimeError(f"Generated certificates for {name} are empty")

                try:
                    from cryptography import x509

                    cert_data = cert_file.read_bytes()
                    loaded_cert = x509.load_pem_x509_certificate(cert_data)
                    _LOGGER.info(
                        "Certificate loaded: subject=%s, valid until %s",
                        loaded_cert.subject.rfc4514_string(),
                        loaded_cert.not_valid_after_utc,
                    )
                except Exception as ex:
                    raise RuntimeError(f"Generated certificate for {name} is invalid: {ex}") from ex

                _LOGGER.info("=== Certificate generation complete for %s ===", name)

            # Create password file
            passwd_file = instance_dir / "passwd"
            if users:
                from auth_manager import AuthManager

                auth_manager = AuthManager(passwd_file)
                for user in users:
                    try:
                        auth_manager.add_user(user["username"], user["password"])
                    except ValueError as ex:
                        _LOGGER.warning("Failed to add user %s: %s", user.get("username"), ex)
            else:
                passwd_file.touch()
                passwd_file.chmod(0o640)
            if passwd_file.exists():
                passwd_file.chmod(0o640)
                resolved = _resolve_effective_user_group()
                if resolved:
                    uid, gid = resolved
                    _maybe_chown(passwd_file, uid, gid)

            # Start Squid process
            success = await self.start_instance(name)
            if not success:
                raise RuntimeError(f"Failed to start Squid process for {name}")

            return {
                "name": name,
                "proxy_type": "squid",
                "port": port,
                "https_enabled": https_enabled,
                "dpi_prevention": dpi_prevention,
                "status": "running",
            }

        except Exception as ex:
            _LOGGER.error("Failed to create instance %s: %s", name, ex)
            raise

    async def _create_tls_tunnel_instance(
        self,
        name: str,
        port: int,
        forward_address: str,
        cover_domain: str | None,
        instance_dir: Path,
        instance_logs_dir: Path,
    ) -> dict[str, Any]:
        """Create a TLS tunnel (nginx SNI multiplexer) instance."""
        name = validate_instance_name(name)
        name = os.path.basename(name)  # CodeQL path-injection sanitiser
        # Verify instance_dir is within CONFIG_DIR (CodeQL path-injection guard)
        if not str(instance_dir.resolve()).startswith(str(CONFIG_DIR.resolve()) + os.sep):
            raise ValueError("instance_dir escapes config directory")
        import json

        # Allocate a local port for the cover website backend
        cover_site_port = port + 10000
        if cover_site_port > 65535:
            cover_site_port = port + 1000
        if cover_site_port > 65535:
            cover_site_port = 9443

        # Generate cover site SSL certificate
        cover_cert_dir = instance_dir / "certs"
        cover_cert_dir.mkdir(parents=True, exist_ok=True)
        cover_cert_dir.chmod(0o750)

        from cert_manager import CertificateManager

        # Use a temporary CertificateManager with instance-local cert dir
        cert_mgr = CertificateManager(instance_dir, "certs")
        # Override cert paths since we're using a non-standard layout
        cert_mgr.cert_dir = cover_cert_dir
        cert_mgr.cert_file = cover_cert_dir / "cover.crt"
        cert_mgr.key_file = cover_cert_dir / "cover.key"

        cn = cover_domain or f"tunnel-{name}"
        cert_file, key_file = await cert_mgr.generate_certificate(
            common_name=cn,
            organization="TLS Tunnel Cover Site",
        )
        _LOGGER.info("Generated cover site certificate for %s (CN: %s)", name, cn)

        # Generate nginx configs
        from tls_tunnel_config import TlsTunnelConfigGenerator

        config_gen = TlsTunnelConfigGenerator(
            instance_name=name,
            listen_port=port,
            forward_address=forward_address,
            cover_site_port=cover_site_port,
            data_dir=str(CONFIG_DIR),
        )

        cover_config_file = instance_dir / "nginx_cover.conf"
        config_gen.generate_cover_site_config(
            cover_config_file,
            cert_path=str(cert_file),
            key_path=str(key_file),
            server_name=cover_domain or "_",
        )

        # Generate stream config with include for cover site
        stream_config_file = instance_dir / "nginx_stream.conf"
        config_gen.generate_stream_config(stream_config_file, cover_config_path=cover_config_file)

        # Save instance metadata
        metadata_file = instance_dir / "instance.json"
        metadata = {
            "name": name,
            "proxy_type": "tls_tunnel",
            "port": port,
            "forward_address": forward_address,
            "cover_domain": cover_domain or "",
            "cover_site_port": cover_site_port,
            "created_at": __import__("datetime").datetime.now().isoformat(),
        }
        metadata_file.write_text(json.dumps(metadata, indent=2))

        # Start nginx
        success = await self.start_instance(name)
        if not success:
            raise RuntimeError(f"Failed to start nginx process for {name}")

        return {
            "name": name,
            "proxy_type": "tls_tunnel",
            "port": port,
            "forward_address": forward_address,
            "cover_domain": cover_domain or "",
            "status": "running",
        }

    async def get_instances(self) -> list[dict[str, Any]]:
        """Get list of all proxy instances."""
        instances: list[dict[str, Any]] = []
        if not CONFIG_DIR.exists():
            return instances

        import json

        for item in CONFIG_DIR.iterdir():
            if not item.is_dir():
                continue

            # Validate directory name to prevent path traversal (CodeQL py/path-injection)
            try:
                name = validate_instance_name(item.name)
            except ValueError:
                continue

            # Re-derive the validated path from CONFIG_DIR + sanitized name
            instance_dir = _safe_path(CONFIG_DIR, name)
            metadata_file = instance_dir / "instance.json"
            has_squid_conf = (instance_dir / "squid.conf").exists()

            # Detect instances: must have instance.json OR squid.conf (legacy)
            if not metadata_file.exists() and not has_squid_conf:
                continue
            is_running = name in self.processes and self.processes[name].poll() is None

            # Read metadata
            port = 3128
            https_enabled = False
            dpi_prevention = False
            proxy_type = "squid"
            forward_address = ""
            cover_domain = ""

            if metadata_file.exists():
                try:
                    metadata = json.loads(metadata_file.read_text())
                    port = metadata.get("port", port)
                    https_enabled = metadata.get("https_enabled", False)
                    dpi_prevention = metadata.get("dpi_prevention", False)
                    proxy_type = metadata.get("proxy_type", "squid")
                    forward_address = metadata.get("forward_address", "")
                    cover_domain = metadata.get("cover_domain", "")
                except Exception as ex:
                    _LOGGER.warning("Failed to read metadata for %s: %s", name, ex)
            elif has_squid_conf:
                # Legacy fallback: parse squid.conf
                try:
                    config_content = (instance_dir / "squid.conf").read_text()
                    import re as _re

                    port_match = _re.search(r"^http_port (\d+)", config_content, _re.MULTILINE)
                    if port_match:
                        port = int(port_match.group(1))
                    https_enabled = "https_port" in config_content
                except Exception as ex:
                    _LOGGER.warning("Failed to parse squid.conf for %s: %s", name, ex)

            instance_data: dict[str, Any] = {
                "name": name,
                "proxy_type": proxy_type,
                "port": port,
                "status": "running" if is_running else "stopped",
                "running": is_running,
            }

            if proxy_type == "tls_tunnel":
                instance_data["forward_address"] = forward_address
                instance_data["cover_domain"] = cover_domain
                instance_data["https_enabled"] = False
                instance_data["dpi_prevention"] = False
            else:
                instance_data["https_enabled"] = https_enabled
                instance_data["dpi_prevention"] = dpi_prevention

                user_count = 0
                passwd_file = instance_dir / "passwd"
                if passwd_file.exists():
                    try:
                        from auth_manager import AuthManager

                        auth_manager = AuthManager(passwd_file)
                        user_count = auth_manager.get_user_count()
                    except Exception as ex:
                        _LOGGER.warning("Failed to read users for %s: %s", name, ex)
                instance_data["user_count"] = user_count

            instances.append(instance_data)
        return instances

    def _save_desired_state(self, name: str, state: str) -> None:
        """Persist the desired state (running/stopped) in instance.json."""
        name = validate_instance_name(name)  # Sanitize before path construction
        import json

        metadata_file = _safe_path(CONFIG_DIR, name, "instance.json")
        if not metadata_file.exists():
            return
        try:
            metadata = json.loads(metadata_file.read_text())
            metadata["desired_state"] = state
            metadata_file.write_text(json.dumps(metadata, indent=2))
        except Exception as ex:
            _LOGGER.warning("Failed to save desired state for %s: %s", name, ex)

    async def restore_desired_states(self) -> None:
        """Restore instance states after addon restart.

        - Instances with desired_state 'running' are started if not already running.
        - Instances with desired_state 'stopped' are stopped if currently running.
        - Instances without desired_state default to 'running' for backward compat.
        """
        import json

        if not CONFIG_DIR.exists():
            return

        for item in CONFIG_DIR.iterdir():
            if not item.is_dir():
                continue
            try:
                name = validate_instance_name(item.name)
            except ValueError:
                continue
            instance_dir = _safe_path(CONFIG_DIR, name)
            if not (instance_dir / "instance.json").exists():
                continue
            # Must have either squid.conf (squid type) or nginx_stream.conf (tls_tunnel type)
            has_config = (instance_dir / "squid.conf").exists() or (
                instance_dir / "nginx_stream.conf"
            ).exists()
            if not has_config:
                continue
            try:
                metadata = json.loads((instance_dir / "instance.json").read_text())
                desired = metadata.get("desired_state", "running")
                is_running = name in self.processes and self.processes[name].poll() is None

                if desired == "running" and not is_running:
                    _LOGGER.info("Restoring desired state: starting instance %s", name)
                    await self.start_instance(name)
                elif desired == "stopped" and is_running:
                    _LOGGER.info("Restoring desired state: stopping instance %s", name)
                    await self.stop_instance(name)
            except Exception as ex:
                _LOGGER.warning("Failed to restore desired state for %s: %s", name, ex)

    def _get_proxy_type(self, name: str) -> str:
        """Read proxy_type from instance.json, defaulting to 'squid'."""
        name = validate_instance_name(name)
        name = os.path.basename(name)  # CodeQL path-injection sanitiser
        import json

        metadata_file = _safe_path(CONFIG_DIR, name, "instance.json")
        if metadata_file.exists():
            try:
                metadata = json.loads(metadata_file.read_text())
                return str(metadata.get("proxy_type", "squid"))
            except Exception:
                _LOGGER.debug("Failed to read proxy_type for %s", name)
        return "squid"

    async def start_instance(self, name: str) -> bool:
        """Start a proxy instance process."""
        name = validate_instance_name(name)
        name = os.path.basename(name)  # CodeQL path-injection sanitiser
        if name in self.processes and self.processes[name].poll() is None:
            _LOGGER.info("Instance %s is already running", name)
            return True

        instance_dir = _safe_path(CONFIG_DIR, name)
        proxy_type = self._get_proxy_type(name)

        if proxy_type == "tls_tunnel":
            return await self._start_tls_tunnel_instance(name, instance_dir)

        return await self._start_squid_instance(name, instance_dir)

    async def _start_tls_tunnel_instance(self, name: str, instance_dir: Path) -> bool:
        """Start an nginx TLS tunnel instance."""
        name = validate_instance_name(name)
        name = os.path.basename(name)  # CodeQL path-injection sanitiser
        # Verify instance_dir is within CONFIG_DIR (CodeQL path-injection guard)
        if not str(instance_dir.resolve()).startswith(str(CONFIG_DIR.resolve()) + os.sep):
            raise ValueError("instance_dir escapes config directory")
        stream_config = instance_dir / "nginx_stream.conf"
        if not stream_config.exists():
            _LOGGER.error("nginx stream config not found for instance %s", name)
            return False

        # Find nginx binary
        import shutil as _shutil

        actual_binary = NGINX_BINARY
        if not os.path.exists(NGINX_BINARY):
            found = _shutil.which("nginx")
            if found:
                actual_binary = found
            else:
                _LOGGER.error("nginx binary not found!")
                return False

        instance_logs_dir = _safe_path(LOGS_DIR, name)
        instance_logs_dir.mkdir(parents=True, exist_ok=True)

        try:
            cmd = [
                actual_binary,
                "-c",
                str(stream_config),
                "-g",
                "daemon off;",
                "-e",
                str(instance_logs_dir / "nginx_error.log"),
            ]

            _LOGGER.info("Starting nginx process for %s: %s", name, " ".join(cmd))

            log_file_path = instance_logs_dir / "nginx_error.log"
            log_output = open(log_file_path, "a", buffering=1)
            log_output.write(
                f"\n--- Starting nginx at {__import__('datetime').datetime.now().isoformat()} ---\n"
            )
            log_output.flush()

            process = subprocess.Popen(  # nosec B603
                cmd,
                stdout=log_output,
                stderr=subprocess.STDOUT,
                text=True,
                preexec_fn=os.setsid,
            )

            # Give nginx a moment to start and check it didn't exit immediately
            await asyncio.sleep(0.5)
            if process.poll() is not None:
                exit_code = process.returncode
                _LOGGER.error("nginx exited immediately for %s (exit code: %d)", name, exit_code)
                return False

            self.processes[name] = process
            self._log_handles[name] = log_output
            _LOGGER.info("nginx process started for %s (PID: %d)", name, process.pid)
            self._save_desired_state(name, "running")
            return True
        except Exception as ex:
            _LOGGER.error("Failed to start nginx for %s: %s", name, ex)
            return False

    async def _start_squid_instance(self, name: str, instance_dir: Path) -> bool:
        """Start a Squid proxy instance."""
        name = validate_instance_name(name)
        name = os.path.basename(name)  # CodeQL path-injection sanitiser
        # Verify instance_dir is within CONFIG_DIR (CodeQL path-injection guard)
        if not str(instance_dir.resolve()).startswith(str(CONFIG_DIR.resolve()) + os.sep):
            raise ValueError("instance_dir escapes config directory")
        config_file = instance_dir / "squid.conf"
        if not config_file.exists():
            _LOGGER.error("Config file not found for instance %s", name)
            return False

        # Ensure instance-specific directories exist
        instance_logs_dir = _safe_path(LOGS_DIR, name)
        instance_logs_dir.mkdir(parents=True, exist_ok=True)
        instance_logs_dir.chmod(0o700)
        resolved = _resolve_effective_user_group()
        if resolved:
            uid, gid = resolved
            _maybe_chown(instance_logs_dir, uid, gid)

        instance_cache_dir = instance_logs_dir / "cache"
        instance_cache_dir.mkdir(parents=True, exist_ok=True)
        instance_cache_dir.chmod(0o700)
        if resolved:
            _maybe_chown(instance_cache_dir, uid, gid)

        # Check for Squid binary
        if not os.path.exists(SQUID_BINARY):
            _LOGGER.error("Squid binary not found at %s", SQUID_BINARY)
            import shutil

            found_squid = shutil.which("squid")
            if found_squid:
                _LOGGER.info("Found Squid at %s via PATH", found_squid)
                actual_binary = found_squid
            else:
                _LOGGER.error("Squid binary not found anywhere!")
                return False
        else:
            actual_binary = SQUID_BINARY

        # Handle HTTPS/SSL certificate verification
        metadata_file = instance_dir / "instance.json"
        if metadata_file.exists():
            try:
                import json

                metadata = json.loads(metadata_file.read_text())
                if metadata.get("https_enabled"):
                    instance_cert_dir = _safe_path(CERTS_DIR, name)
                    cert_file = instance_cert_dir / "squid.crt"
                    key_file = instance_cert_dir / "squid.key"

                    if not cert_file.exists() or not key_file.exists():
                        raise RuntimeError(f"HTTPS enabled but certificates missing for {name}")

                    # Fix permissions if needed
                    for cert_path in (cert_file, key_file):
                        if cert_path.stat().st_mode & 0o777 != 0o640:
                            cert_path.chmod(0o640)
                        resolved = _resolve_effective_user_group()
                        if resolved:
                            uid, gid = resolved
                            _maybe_chown(cert_path, uid, gid)

                    # Validate certificate
                    try:
                        import subprocess as sp  # nosec B404

                        result = sp.run(  # nosec B603,B607
                            ["openssl", "x509", "-in", str(cert_file), "-noout", "-text"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if result.returncode != 0:
                            raise RuntimeError(
                                f"Certificate validation failed for {name}: {result.stderr}"
                            )
                        _LOGGER.info("Certificate validated for %s", name)
                    except FileNotFoundError:
                        _LOGGER.warning("OpenSSL not found, skipping cert validation")

                    # Verify readable
                    try:
                        with open(cert_file) as fh:
                            fh.read(1)
                        with open(key_file) as fh:
                            fh.read(1)
                    except Exception as ex:
                        raise RuntimeError(
                            f"Cannot read certificate files for {name}: {ex}"
                        ) from ex

                    _LOGGER.info("Verified HTTPS certificates for %s", name)
            except Exception as ex:
                _LOGGER.error("Error during HTTPS certificate check for %s: %s", name, ex)
                raise

        # Initialize cache if needed
        try:
            subprocess.run(  # nosec B603
                [actual_binary, "-z", "-f", str(config_file)],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            _LOGGER.warning(
                "Cache initialization returned non-zero for %s: %s", name, e.stderr.decode()
            )
        except Exception as ex:
            _LOGGER.warning("Failed to run cache initialization for %s: %s", name, ex)

        try:
            cmd = [actual_binary, "-N", "-f", str(config_file)]
            _LOGGER.info("Starting Squid process for %s: %s", name, " ".join(cmd))

            log_file_path = instance_logs_dir / "cache.log"
            log_output = open(log_file_path, "a", buffering=1)
            log_output.write(
                f"\n--- Starting Squid at {__import__('datetime').datetime.now().isoformat()} ---\n"
            )
            log_output.write(f"Command: {' '.join(cmd)}\n")
            log_output.flush()

            process = subprocess.Popen(  # nosec B603
                cmd,
                stdout=log_output,
                stderr=subprocess.STDOUT,
                text=True,
                preexec_fn=os.setsid,
            )

            self.processes[name] = process
            self._log_handles[name] = log_output
            _LOGGER.info("Squid process started for %s (PID: %d)", name, process.pid)
            self._save_desired_state(name, "running")
            return True
        except Exception as ex:
            _LOGGER.error("Failed to start Squid process for %s: %s", name, ex)
            return False

    async def stop_instance(self, name: str) -> bool:
        """Stop a proxy instance process."""
        if name not in self.processes:
            _LOGGER.warning("No process found for instance %s", name)
            self._save_desired_state(name, "stopped")
            return True

        process = self.processes[name]
        if process.poll() is not None:
            _LOGGER.info("Instance %s is already stopped", name)
            del self.processes[name]
            self._save_desired_state(name, "stopped")
            return True

        proxy_type = self._get_proxy_type(name)

        try:
            _LOGGER.info("Stopping %s process for %s (PID: %d)", proxy_type, name, process.pid)

            if proxy_type == "tls_tunnel":
                # nginx: SIGQUIT for graceful shutdown, then SIGTERM
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGQUIT)
                except ProcessLookupError:
                    pass
            else:
                # Squid: SIGTERM to the process group
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass  # Already dead

            # Wait for process to terminate
            stopped = False
            for _ in range(10):
                if process.poll() is not None:
                    stopped = True
                    break
                await asyncio.sleep(0.5)

            if not stopped:
                _LOGGER.warning("Process %d didn't stop, sending SIGKILL", process.pid)
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Already dead

            # Reap the zombie and ensure the process is fully gone
            for _ in range(10):
                if process.poll() is not None:
                    break
                await asyncio.sleep(0.3)
            # Final synchronous reap (non-blocking since process should be dead)
            try:
                process.wait(timeout=0)
            except subprocess.TimeoutExpired:
                _LOGGER.debug("Process %s still alive after reap attempt", name)

            if name in self.processes:
                del self.processes[name]
            if name in self._log_handles:
                try:
                    self._log_handles.pop(name).close()
                except Exception:  # nosec B110 — best-effort cleanup
                    _LOGGER.debug("Failed to close log handle for %s", name)
            _LOGGER.info("Process stopped for %s", name)
            self._save_desired_state(name, "stopped")
            return True
        except Exception as ex:
            _LOGGER.error("Failed to stop process for %s: %s", name, ex)
            # Clean up the process entry even on failure
            if name in self.processes:
                del self.processes[name]
            if name in self._log_handles:
                try:
                    self._log_handles.pop(name).close()
                except Exception:  # nosec B110 — best-effort cleanup
                    _LOGGER.debug("Failed to close log handle for %s", name)
            return False

    async def remove_instance(self, name: str) -> bool:
        """Remove a proxy instance and its configuration."""
        name = validate_instance_name(name)
        # Stop instance first
        stopped = await self.stop_instance(name)
        if not stopped:
            _LOGGER.warning("Failed to stop instance %s, attempting removal anyway", name)

        # Wait a bit for process to fully terminate
        await asyncio.sleep(1)

        instance_dir = _safe_path(CONFIG_DIR, name)
        instance_logs_dir = _safe_path(LOGS_DIR, name)
        instance_cert_dir = _safe_path(CERTS_DIR, name)

        try:
            import shutil

            # Remove all instance directories
            for directory in [instance_dir, instance_logs_dir, instance_cert_dir]:
                if directory.exists():
                    shutil.rmtree(directory)
                    _LOGGER.debug("Removed directory: %s", directory)

            # Clean up process entry if still present
            if name in self.processes:
                del self.processes[name]

            _LOGGER.info("✓ Instance %s removed", name)
            return True
        except Exception as ex:
            _LOGGER.error("Failed to remove instance %s: %s", name, ex)
            return False

    async def get_users(self, name: str) -> list[str]:
        """Get list of users for an instance."""
        name = validate_instance_name(name)
        instance_dir = _safe_path(CONFIG_DIR, name)
        passwd_file = instance_dir / "passwd"

        if not passwd_file.exists():
            return []

        try:
            from auth_manager import AuthManager

            auth_manager = AuthManager(passwd_file)
            return auth_manager.get_users()
        except Exception as ex:
            _LOGGER.error("Failed to list users for %s: %s", name, ex)
            return []

    async def add_user(self, name: str, username: str, password: str) -> bool:
        """Add a user to an instance."""
        name = validate_instance_name(name)
        instance_dir = _safe_path(CONFIG_DIR, name)
        passwd_file = instance_dir / "passwd"

        try:
            from auth_manager import AuthManager

            auth_manager = AuthManager(passwd_file)
            if not auth_manager.add_user(username, password):
                raise ValueError(f"User {username} already exists")

            # Ensure password file is written and has correct permissions

            if passwd_file.exists():
                passwd_file.chmod(0o640)
                resolved = _resolve_effective_user_group()
                if resolved:
                    uid, gid = resolved
                    _maybe_chown(passwd_file, uid, gid)
                # Verify file was written by checking it's not empty (if users exist)
                if passwd_file.stat().st_size == 0 and auth_manager.get_user_count() > 0:
                    _LOGGER.warning("Password file appears empty after adding user, retrying save")
                    auth_manager._save_users()

            _LOGGER.info("✓ Added user %s to instance %s", username, name)

            # Restart if running to apply changes - with better error handling
            if name in self.processes:
                stopped = await self.stop_instance(name)
                if not stopped:
                    _LOGGER.error("Failed to stop instance %s for user update", name)
                    return False
                # Wait for process to fully stop
                await asyncio.sleep(1)

                started = await self.start_instance(name)
                if not started:
                    _LOGGER.error("Failed to restart instance %s after user update", name)
                    return False
                # Wait for Squid to fully start and load auth
                await asyncio.sleep(2)
                _LOGGER.info("Instance %s restarted successfully with new user", name)

            return True
        except ValueError:
            # Re-raise validation errors to be handled by the API
            raise
        except Exception as ex:
            _LOGGER.error("Failed to add user to %s: %s", name, ex)
            return False

    async def remove_user(self, name: str, username: str) -> bool:
        """Remove a user from an instance."""
        name = validate_instance_name(name)
        instance_dir = _safe_path(CONFIG_DIR, name)
        passwd_file = instance_dir / "passwd"

        try:
            from auth_manager import AuthManager

            auth_manager = AuthManager(passwd_file)
            if not auth_manager.remove_user(username):
                _LOGGER.warning("User %s does not exist in instance %s", username, name)
                return False

            # Ensure password file is written
            if passwd_file.exists():
                passwd_file.chmod(0o640)
                resolved = _resolve_effective_user_group()
                if resolved:
                    uid, gid = resolved
                    _maybe_chown(passwd_file, uid, gid)

            _LOGGER.info("✓ Removed user %s from instance %s", username, name)

            # Restart if running to apply changes - with better error handling
            if name in self.processes:
                stopped = await self.stop_instance(name)
                if not stopped:
                    _LOGGER.error("Failed to stop instance %s for user removal", name)
                    return False
                # Wait for process to fully stop
                await asyncio.sleep(1)

                started = await self.start_instance(name)
                if not started:
                    _LOGGER.error("Failed to restart instance %s after user removal", name)
                    return False
                # Wait for Squid to fully start and load auth
                await asyncio.sleep(2)
                _LOGGER.info("Instance %s restarted successfully after user removal", name)

            return True
        except Exception as ex:
            _LOGGER.error("Failed to remove user from %s: %s", name, ex)
            return False

    async def update_instance(
        self,
        name: str,
        port: int | None = None,
        https_enabled: bool | None = None,
        cert_params: dict[str, Any] | None = None,
        dpi_prevention: bool | None = None,
        forward_address: str | None = None,
        cover_domain: str | None = None,
    ) -> bool:
        """Update instance configuration."""
        name = validate_instance_name(name)
        instance_dir = _safe_path(CONFIG_DIR, name)
        if not instance_dir.exists():
            return False

        try:
            import json

            metadata_file = instance_dir / "instance.json"
            if not metadata_file.exists():
                current_port = 3128
                current_https = False
                current_dpi = False
                proxy_type = "squid"
                metadata = {}
            else:
                metadata = json.loads(metadata_file.read_text())
                current_port = metadata.get("port", 3128)
                current_https = metadata.get("https_enabled", False)
                current_dpi = metadata.get("dpi_prevention", False)
                proxy_type = metadata.get("proxy_type", "squid")

            new_port = port if port is not None else current_port
            validate_port(new_port)

            if proxy_type == "tls_tunnel":
                return await self._update_tls_tunnel_instance(
                    name, new_port, forward_address, cover_domain, metadata, instance_dir
                )

            # --- Squid update (existing behavior) ---
            new_https = https_enabled if https_enabled is not None else current_https
            new_dpi = dpi_prevention if dpi_prevention is not None else current_dpi

            # Preserve existing fields
            metadata.update(
                {
                    "name": name,
                    "proxy_type": "squid",
                    "port": new_port,
                    "https_enabled": new_https,
                    "dpi_prevention": new_dpi,
                    "updated_at": __import__("datetime").datetime.now().isoformat(),
                }
            )
            metadata_file.write_text(json.dumps(metadata, indent=2))

            # Regenerate Squid configuration
            from squid_config import SquidConfigGenerator

            config_gen = SquidConfigGenerator(
                name, new_port, new_https, str(CONFIG_DIR), dpi_prevention=new_dpi
            )
            config_file = instance_dir / "squid.conf"
            config_gen.generate_config(config_file)
            resolved = _resolve_effective_user_group()
            if resolved:
                uid, gid = resolved
                _maybe_chown(config_file, uid, gid)

            # Handle HTTPS certificate
            if new_https:
                from cert_manager import CertificateManager

                instance_cert_dir = _safe_path(CERTS_DIR, name)
                if instance_cert_dir.exists():
                    import shutil

                    shutil.rmtree(instance_cert_dir, ignore_errors=True)

                instance_cert_dir.mkdir(parents=True, exist_ok=True)
                instance_cert_dir.chmod(0o750)
                resolved = _resolve_effective_user_group()
                if resolved:
                    uid, gid = resolved
                    _maybe_chown(instance_cert_dir, uid, gid)

                cert_manager = CertificateManager(CERTS_DIR, name)
                cert_params = cert_params or {}
                cert_file, key_file = await cert_manager.generate_certificate(
                    validity_days=cert_params.get("validity_days", 365),
                    key_size=cert_params.get("key_size", 2048),
                    common_name=cert_params.get("common_name"),
                    country=cert_params.get("country", "US"),
                    organization=cert_params.get("organization", "Squid Proxy Manager"),
                )

                await asyncio.sleep(0.5)
                if not cert_file.exists() or not key_file.exists():
                    raise RuntimeError(f"Failed to generate certificates for {name}")
                if cert_file.stat().st_size == 0 or key_file.stat().st_size == 0:
                    raise RuntimeError(f"Generated certificates for {name} are empty")

                try:
                    from cryptography import x509

                    x509.load_pem_x509_certificate(cert_file.read_bytes())
                except Exception as ex:
                    raise RuntimeError(f"Generated certificate for {name} is invalid: {ex}") from ex

                _LOGGER.info("Generated HTTPS certificates for instance %s", name)

            _LOGGER.info("Updated configuration for instance %s", name)

            # Restart if running to apply changes
            if name in self.processes:
                stopped = await self.stop_instance(name)
                if not stopped:
                    _LOGGER.warning("Failed to stop instance %s before restart", name)
                await asyncio.sleep(1)
                started = await self.start_instance(name)
                if not started:
                    raise RuntimeError(f"Failed to restart instance {name} after update")
                await asyncio.sleep(2)

            return True
        except Exception as ex:
            _LOGGER.error("Failed to update instance %s: %s", name, ex)
            return False

    async def _update_tls_tunnel_instance(
        self,
        name: str,
        new_port: int,
        forward_address: str | None,
        cover_domain: str | None,
        metadata: dict[str, Any],
        instance_dir: Path,
    ) -> bool:
        """Update a TLS tunnel instance configuration."""
        name = validate_instance_name(name)
        name = os.path.basename(name)  # CodeQL path-injection sanitiser
        # Verify instance_dir is within CONFIG_DIR (CodeQL path-injection guard)
        if not str(instance_dir.resolve()).startswith(str(CONFIG_DIR.resolve()) + os.sep):
            raise ValueError("instance_dir escapes config directory")
        import json

        current_forward = metadata.get("forward_address", "")
        current_cover = metadata.get("cover_domain", "")
        cover_site_port = metadata.get("cover_site_port", new_port + 10000)

        new_forward = forward_address if forward_address is not None else current_forward
        new_cover = cover_domain if cover_domain is not None else current_cover

        if not new_forward:
            raise ValueError("forward_address cannot be empty for TLS tunnel instances")

        from tls_tunnel_config import validate_forward_address

        validate_forward_address(new_forward)

        # Update metadata
        metadata.update(
            {
                "port": new_port,
                "forward_address": new_forward,
                "cover_domain": new_cover,
                "updated_at": __import__("datetime").datetime.now().isoformat(),
            }
        )
        metadata_file = instance_dir / "instance.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))

        # Regenerate nginx configs
        from tls_tunnel_config import TlsTunnelConfigGenerator

        config_gen = TlsTunnelConfigGenerator(
            instance_name=name,
            listen_port=new_port,
            forward_address=new_forward,
            cover_site_port=cover_site_port,
            data_dir=str(CONFIG_DIR),
        )

        cover_cert_dir = instance_dir / "certs"
        cert_file = cover_cert_dir / "cover.crt"
        key_file = cover_cert_dir / "cover.key"

        cover_config_file = instance_dir / "nginx_cover.conf"
        config_gen.generate_cover_site_config(
            cover_config_file,
            cert_path=str(cert_file),
            key_path=str(key_file),
            server_name=new_cover or "_",
        )

        # Generate stream config with include for cover site
        stream_config_file = instance_dir / "nginx_stream.conf"
        config_gen.generate_stream_config(stream_config_file, cover_config_path=cover_config_file)

        _LOGGER.info("Updated TLS tunnel configuration for instance %s", name)

        # Restart if running
        if name in self.processes:
            stopped = await self.stop_instance(name)
            if not stopped:
                _LOGGER.warning("Failed to stop instance %s before restart", name)
            await asyncio.sleep(1)
            started = await self.start_instance(name)
            if not started:
                raise RuntimeError(f"Failed to restart instance {name} after update")
            await asyncio.sleep(1)

        return True

    async def regenerate_certs(self, name: str, cert_params: dict[str, Any] | None = None) -> bool:
        """Regenerate HTTPS certificates for an instance."""
        instance_dir = _safe_path(CONFIG_DIR, name)
        if not instance_dir.exists():
            return False

        try:
            # Remove old certificates
            instance_cert_dir = _safe_path(CERTS_DIR, name)
            if instance_cert_dir.exists():
                import shutil

                shutil.rmtree(instance_cert_dir, ignore_errors=True)

            instance_cert_dir.mkdir(parents=True, exist_ok=True)
            instance_cert_dir.chmod(0o750)
            resolved = _resolve_effective_user_group()
            if resolved:
                uid, gid = resolved
                _maybe_chown(instance_cert_dir, uid, gid)

            from cert_manager import CertificateManager

            cert_manager = CertificateManager(CERTS_DIR, name)
            cert_params = cert_params or {}
            cert_file, key_file = await cert_manager.generate_certificate(
                validity_days=cert_params.get("validity_days", 365),
                key_size=cert_params.get("key_size", 2048),
                common_name=cert_params.get("common_name"),
                country=cert_params.get("country", "US"),
                organization=cert_params.get("organization", "Squid Proxy Manager"),
            )

            # Verify certificates
            if not cert_file.exists() or not key_file.exists():
                raise RuntimeError(f"Failed to generate certificates for {name}")

            # Verify certificate can be loaded
            try:
                from cryptography import x509

                cert_data = cert_file.read_bytes()
                x509.load_pem_x509_certificate(cert_data)
            except Exception as ex:
                raise RuntimeError(f"Generated certificate for {name} is invalid: {ex}") from ex
            _LOGGER.info("✓ Regenerated certificates for instance %s", name)

            # Restart if running to apply changes (robust stop/start)
            if name in self.processes:
                stopped = await self.stop_instance(name)
                if not stopped:
                    _LOGGER.warning("Failed to stop instance %s before restart", name)
                # Wait for process to fully stop
                await asyncio.sleep(1)
                started = await self.start_instance(name)
                if not started:
                    raise RuntimeError(f"Failed to restart instance {name} after cert regeneration")
                # Wait for Squid to fully start and load config
                await asyncio.sleep(2)

            return True
        except Exception as ex:
            _LOGGER.error("Failed to regenerate certificates for %s: %s", name, ex)
            return False
