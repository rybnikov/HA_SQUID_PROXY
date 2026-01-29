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
            instance_logs_dir = LOGS_DIR / name
            instance_logs_dir.mkdir(parents=True, exist_ok=True)

            # Generate Squid configuration
            from squid_config import SquidConfigGenerator

            config_gen = SquidConfigGenerator(name, port, https_enabled)
            config_file = instance_dir / "squid.conf"
            config_gen.generate_config(config_file)

            # Handle HTTPS certificate
            cert_file = None
            key_file = None
            if https_enabled:
                from cert_manager import CertificateManager

                cert_manager = CertificateManager(CERTS_DIR, name)
                cert_file, key_file = await cert_manager.generate_certificate()

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
                passwd_file.chmod(0o600)

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

        for item in CONFIG_DIR.iterdir():
            if item.is_dir() and (item / "squid.conf").exists():
                name = item.name
                is_running = name in self.processes and self.processes[name].poll() is None
                instances.append(
                    {
                        "name": name,
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

        try:
            # Command to run Squid in foreground (-N) with specific config (-f)
            cmd = [
                SQUID_BINARY,
                "-N",  # No daemon mode
                "-f",
                str(config_file),
            ]

            _LOGGER.info("Starting Squid process for %s: %s", name, " ".join(cmd))

            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
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
        await self.stop_instance(name)

        instance_dir = CONFIG_DIR / name
        instance_logs_dir = LOGS_DIR / name

        try:
            import shutil

            if instance_dir.exists():
                shutil.rmtree(instance_dir)
            if instance_logs_dir.exists():
                shutil.rmtree(instance_logs_dir)
            _LOGGER.info("✓ Instance %s removed", name)
            return True
        except Exception as ex:
            _LOGGER.error("Failed to remove instance %s: %s", name, ex)
            return False
