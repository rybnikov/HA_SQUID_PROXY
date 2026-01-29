#!/usr/bin/env python3
"""Proxy instance management for the add-on using OS processes."""
import asyncio
import logging
import os
import signal
import subprocess
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("/data")
CONFIG_DIR = DATA_DIR / "squid_proxy_manager"
CERTS_DIR = CONFIG_DIR / "certs"
LOGS_DIR = CONFIG_DIR / "logs"
SQUID_BINARY = "/usr/sbin/squid"


class ProxyInstanceManager:
    """Manages Squid proxy instances as OS processes."""

    def __init__(self):
        """Initialize the manager."""
        self.processes: dict[str, subprocess.Popen] = {}
        # Ensure directories exist
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CERTS_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        _LOGGER.info("ProxyInstanceManager initialized using process-based architecture")

    async def create_instance(
        self,
        name: str,
        port: int,
        https_enabled: bool = False,
        users: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Create and start a new proxy instance.

        Args:
            name: Instance name
            port: Port number
            https_enabled: Whether HTTPS is enabled
            users: List of users with username/password

        Returns:
            Dictionary with instance information
        """
        try:
            # If instance already exists, stop it first to ensure clean start with new config/users
            if name in self.processes:
                _LOGGER.info("Instance %s already exists, stopping for recreation", name)
                await self.stop_instance(name)

            # Create directories
            instance_dir = CONFIG_DIR / name

            # Clean up any leftover directories from Docker volume mounts
            # Docker often creates directories when mounting non-existent files
            for problematic_path in [
                instance_dir / "squid.conf",
                instance_dir / "passwd",
                CERTS_DIR / name / "squid.crt",
                CERTS_DIR / name / "squid.key",
            ]:
                if problematic_path.exists() and problematic_path.is_dir():
                    _LOGGER.info("Cleaning up problematic directory: %s", problematic_path)
                    import shutil

                    shutil.rmtree(problematic_path)

            instance_dir.mkdir(parents=True, exist_ok=True)
            instance_dir.chmod(0o755)
            instance_logs_dir = LOGS_DIR / name
            instance_logs_dir.mkdir(parents=True, exist_ok=True)

            # Generate Squid configuration
            from squid_config import SquidConfigGenerator

            config_gen = SquidConfigGenerator(name, port, https_enabled)
            config_file = instance_dir / "squid.conf"
            config_gen.generate_config(config_file)

            # Save instance metadata for easier retrieval
            import json

            metadata_file = instance_dir / "instance.json"
            metadata = {
                "name": name,
                "port": port,
                "https_enabled": https_enabled,
                "created_at": __import__("datetime").datetime.now().isoformat(),
            }
            metadata_file.write_text(json.dumps(metadata, indent=2))

            # Handle HTTPS certificate
            cert_file = None
            key_file = None
            if https_enabled:
                # Ensure certificate directory exists
                instance_cert_dir = CERTS_DIR / name
                instance_cert_dir.mkdir(parents=True, exist_ok=True)
                instance_cert_dir.chmod(0o755)
                
                from cert_manager import CertificateManager

                cert_manager = CertificateManager(CERTS_DIR, name)
                cert_file, key_file = await cert_manager.generate_certificate()
                
                # Wait a moment to ensure files are fully written
                await asyncio.sleep(0.5)
                
                # Verify certificates were created and are readable
                if not cert_file.exists() or not key_file.exists():
                    raise RuntimeError(f"Failed to generate certificates for {name}")
                
                # Verify file sizes (should be > 0)
                if cert_file.stat().st_size == 0 or key_file.stat().st_size == 0:
                    raise RuntimeError(f"Generated certificates for {name} are empty")
                
                _LOGGER.info("✓ Generated HTTPS certificates for instance %s (cert: %d bytes, key: %d bytes)", 
                           name, cert_file.stat().st_size, key_file.stat().st_size)

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
                # Create empty password file if no users
                passwd_file.touch()
                passwd_file.chmod(0o644)

            # Start Squid process
            success = await self.start_instance(name)
            if not success:
                raise RuntimeError(f"Failed to start Squid process for {name}")

            return {
                "name": name,
                "port": port,
                "https_enabled": https_enabled,
                "status": "running",
            }

        except Exception as ex:
            _LOGGER.error("Failed to create instance %s: %s", name, ex)
            raise

    async def get_instances(self) -> list[dict[str, Any]]:
        """Get list of all proxy instances."""
        instances: list[dict[str, Any]] = []
        # List directories in CONFIG_DIR to find instances
        if not CONFIG_DIR.exists():
            return instances

        import json

        for item in CONFIG_DIR.iterdir():
            if item.is_dir() and (item / "squid.conf").exists():
                name = item.name
                is_running = name in self.processes and self.processes[name].poll() is None

                # Try to read metadata from instance.json
                port = 3128
                https_enabled = False
                metadata_file = item / "instance.json"

                if metadata_file.exists():
                    try:
                        metadata = json.loads(metadata_file.read_text())
                        port = metadata.get("port", port)
                        https_enabled = metadata.get("https_enabled", False)
                    except Exception as ex:
                        _LOGGER.warning("Failed to read metadata for %s: %s", name, ex)
                else:
                    # Fallback to parsing squid.conf if metadata doesn't exist (legacy)
                    try:
                        config_content = (item / "squid.conf").read_text()
                        import re

                        port_match = re.search(r"^http_port (\d+)", config_content, re.MULTILINE)
                        if port_match:
                            port = int(port_match.group(1))
                        https_enabled = "https_port" in config_content
                    except Exception:
                        pass

                instances.append(
                    {
                        "name": name,
                        "port": port,
                        "https_enabled": https_enabled,
                        "status": "running" if is_running else "stopped",
                        "running": is_running,
                    }
                )
        return instances

    async def start_instance(self, name: str) -> bool:
        """Start a proxy instance process."""
        if name in self.processes and self.processes[name].poll() is None:
            _LOGGER.info("Instance %s is already running", name)
            return True

        instance_dir = CONFIG_DIR / name
        config_file = instance_dir / "squid.conf"

        if not config_file.exists():
            _LOGGER.error("Config file not found for instance %s", name)
            return False

        # Ensure instance-specific directories exist
        instance_logs_dir = LOGS_DIR / name
        instance_logs_dir.mkdir(parents=True, exist_ok=True)
        # Ensure world-writable for Squid if it drops privileges
        instance_logs_dir.chmod(0o777)

        instance_cache_dir = instance_logs_dir / "cache"
        instance_cache_dir.mkdir(parents=True, exist_ok=True)
        instance_cache_dir.chmod(0o777)

        # Check for Squid binary
        if not os.path.exists(SQUID_BINARY):
            _LOGGER.error("Squid binary not found at %s", SQUID_BINARY)
            # Try to find it in path as fallback
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
                    instance_cert_dir = CERTS_DIR / name
                    cert_file = instance_cert_dir / "squid.crt"
                    key_file = instance_cert_dir / "squid.key"
                    
                    # Verify certificates exist
                    if not cert_file.exists() or not key_file.exists():
                        _LOGGER.error(
                            "HTTPS enabled for %s but certificates missing! cert=%s exists=%s, key=%s exists=%s",
                            name,
                            cert_file,
                            cert_file.exists(),
                            key_file,
                            key_file.exists(),
                        )
                        raise RuntimeError(
                            f"HTTPS enabled but certificates missing for {name}. "
                            f"Cert: {cert_file} (exists: {cert_file.exists()}), "
                            f"Key: {key_file} (exists: {key_file.exists()})"
                        )
                    
                    # Verify certificate file permissions
                    if cert_file.exists():
                        cert_stat = cert_file.stat()
                        if cert_stat.st_mode & 0o777 != 0o644:
                            _LOGGER.warning("Fixing certificate permissions for %s", name)
                            cert_file.chmod(0o644)
                    
                    if key_file.exists():
                        key_stat = key_file.stat()
                        if key_stat.st_mode & 0o777 != 0o600:
                            _LOGGER.warning("Fixing key permissions for %s", name)
                            key_file.chmod(0o600)
                    
                    _LOGGER.info("✓ Verified HTTPS certificates for %s", name)
            except Exception as ex:
                _LOGGER.error("Error during HTTPS certificate check for %s: %s", name, ex)
                raise

        # Initialize cache if needed
        try:
            _LOGGER.info("Initializing cache for %s...", name)
            subprocess.run(
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
            # Command to run Squid in foreground (-N) with specific config (-f)
            cmd = [
                actual_binary,
                "-N",  # No daemon mode
                "-f",
                str(config_file),
            ]

            _LOGGER.info("Starting Squid process for %s: %s", name, " ".join(cmd))

            # Open log file for redirection of stdout/stderr
            # This ensures Squid doesn't hang on a full pipe and early errors are captured
            log_file_path = instance_logs_dir / "cache.log"
            log_output = open(log_file_path, "a", buffering=1)  # Line buffered
            log_output.write(
                f"\n--- Starting Squid at {__import__('datetime').datetime.now().isoformat()} ---\n"
            )
            log_output.write(f"Command: {' '.join(cmd)}\n")
            log_output.flush()

            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=log_output,
                stderr=subprocess.STDOUT,
                text=True,
                preexec_fn=os.setsid,  # Create new process group
            )

            self.processes[name] = process
            _LOGGER.info("✓ Squid process started for %s (PID: %d)", name, process.pid)
            return True
        except Exception as ex:
            _LOGGER.error("Failed to start Squid process for %s: %s", name, ex)
            return False

    async def stop_instance(self, name: str) -> bool:
        """Stop a proxy instance process."""
        if name not in self.processes:
            _LOGGER.warning("No process found for instance %s", name)
            return True

        process = self.processes[name]
        if process.poll() is not None:
            _LOGGER.info("Instance %s is already stopped", name)
            del self.processes[name]
            return True

        try:
            _LOGGER.info("Stopping Squid process for %s (PID: %d)", name, process.pid)
            # Send SIGTERM to the process group
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)

            # Wait for process to terminate
            for _ in range(10):
                if process.poll() is not None:
                    break
                await asyncio.sleep(0.5)

            if process.poll() is None:
                _LOGGER.warning("Process %d didn't stop, sending SIGKILL", process.pid)
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)

            del self.processes[name]
            _LOGGER.info("✓ Squid process stopped for %s", name)
            return True
        except Exception as ex:
            _LOGGER.error("Failed to stop Squid process for %s: %s", name, ex)
            return False

    async def remove_instance(self, name: str) -> bool:
        """Remove a proxy instance and its configuration."""
        # Stop instance first
        stopped = await self.stop_instance(name)
        if not stopped:
            _LOGGER.warning("Failed to stop instance %s, attempting removal anyway", name)

        # Wait a bit for process to fully terminate
        await asyncio.sleep(1)

        instance_dir = CONFIG_DIR / name
        instance_logs_dir = LOGS_DIR / name
        instance_cert_dir = CERTS_DIR / name

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
        instance_dir = CONFIG_DIR / name
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
        instance_dir = CONFIG_DIR / name
        passwd_file = instance_dir / "passwd"

        try:
            from auth_manager import AuthManager

            auth_manager = AuthManager(passwd_file)
            if not auth_manager.add_user(username, password):
                raise ValueError(f"User {username} already exists")

            # Ensure password file is written and has correct permissions
            import os
            if passwd_file.exists():
                passwd_file.chmod(0o644)
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
        instance_dir = CONFIG_DIR / name
        passwd_file = instance_dir / "passwd"

        try:
            from auth_manager import AuthManager

            auth_manager = AuthManager(passwd_file)
            if not auth_manager.remove_user(username):
                _LOGGER.warning("User %s does not exist in instance %s", username, name)
                return False

            # Ensure password file is written
            if passwd_file.exists():
                passwd_file.chmod(0o644)

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
        self, name: str, port: int | None = None, https_enabled: bool | None = None
    ) -> bool:
        """Update instance configuration."""
        instance_dir = CONFIG_DIR / name
        if not instance_dir.exists():
            return False

        try:
            import json

            metadata_file = instance_dir / "instance.json"
            if not metadata_file.exists():
                # Fallback to defaults
                current_port = 3128
                current_https = False
            else:
                metadata = json.loads(metadata_file.read_text())
                current_port = metadata.get("port", 3128)
                current_https = metadata.get("https_enabled", False)

            new_port = port if port is not None else current_port
            new_https = https_enabled if https_enabled is not None else current_https

            # Update metadata
            metadata = {
                "name": name,
                "port": new_port,
                "https_enabled": new_https,
                "updated_at": __import__("datetime").datetime.now().isoformat(),
            }
            metadata_file.write_text(json.dumps(metadata, indent=2))

            # Regenerate Squid configuration
            from squid_config import SquidConfigGenerator

            config_gen = SquidConfigGenerator(name, new_port, new_https)
            config_file = instance_dir / "squid.conf"
            config_gen.generate_config(config_file)

            # Handle HTTPS certificate if enabled and changed
            if new_https and not current_https:
                from cert_manager import CertificateManager

                # Ensure certificate directory exists
                instance_cert_dir = CERTS_DIR / name
                instance_cert_dir.mkdir(parents=True, exist_ok=True)
                instance_cert_dir.chmod(0o755)

                cert_manager = CertificateManager(CERTS_DIR, name)
                cert_file, key_file = await cert_manager.generate_certificate()
                
                # Wait a moment to ensure files are fully written
                await asyncio.sleep(0.5)
                
                # Verify certificates were created and are readable
                if not cert_file.exists() or not key_file.exists():
                    raise RuntimeError(f"Failed to generate certificates for {name}")
                
                # Verify file sizes (should be > 0)
                if cert_file.stat().st_size == 0 or key_file.stat().st_size == 0:
                    raise RuntimeError(f"Generated certificates for {name} are empty")
                
                _LOGGER.info("✓ Generated HTTPS certificates for instance %s (cert: %d bytes, key: %d bytes)", 
                           name, cert_file.stat().st_size, key_file.stat().st_size)
            elif new_https and current_https:
                # HTTPS was already enabled, verify certificates exist
                instance_cert_dir = CERTS_DIR / name
                cert_file = instance_cert_dir / "squid.crt"
                key_file = instance_cert_dir / "squid.key"
                
                if not cert_file.exists() or not key_file.exists():
                    _LOGGER.warning("HTTPS enabled but certificates missing for %s, regenerating...", name)
                    # Ensure certificate directory exists
                    instance_cert_dir.mkdir(parents=True, exist_ok=True)
                    instance_cert_dir.chmod(0o755)
                    
                    from cert_manager import CertificateManager
                    cert_manager = CertificateManager(CERTS_DIR, name)
                    cert_file, key_file = await cert_manager.generate_certificate()
                    
                    # Wait a moment to ensure files are fully written
                    await asyncio.sleep(0.5)
                    
                    if not cert_file.exists() or not key_file.exists():
                        raise RuntimeError(f"Failed to generate certificates for {name}")
                    
                    # Verify file sizes
                    if cert_file.stat().st_size == 0 or key_file.stat().st_size == 0:
                        raise RuntimeError(f"Generated certificates for {name} are empty")

            _LOGGER.info("✓ Updated configuration for instance %s", name)

            # Restart if running to apply changes
            if name in self.processes:
                stopped = await self.stop_instance(name)
                if not stopped:
                    _LOGGER.warning("Failed to stop instance %s before restart", name)
                await asyncio.sleep(1)  # Wait for process to fully stop
                started = await self.start_instance(name)
                if not started:
                    raise RuntimeError(f"Failed to restart instance {name} after update")
                await asyncio.sleep(2)  # Wait for Squid to fully start and load config

            return True
        except Exception as ex:
            _LOGGER.error("Failed to update instance %s: %s", name, ex)
            return False

    async def regenerate_certs(self, name: str) -> bool:
        """Regenerate HTTPS certificates for an instance."""
        instance_dir = CONFIG_DIR / name
        if not instance_dir.exists():
            return False

        try:
            from cert_manager import CertificateManager

            cert_manager = CertificateManager(CERTS_DIR, name)
            await cert_manager.generate_certificate()
            _LOGGER.info("✓ Regenerated certificates for instance %s", name)

            # Restart if running to apply changes
            if name in self.processes:
                await self.stop_instance(name)
                await self.start_instance(name)

            return True
        except Exception as ex:
            _LOGGER.error("Failed to regenerate certificates for %s: %s", name, ex)
            return False
